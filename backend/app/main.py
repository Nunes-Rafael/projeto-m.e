import os
import json
import re
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agent import AgentConfigurationError, AgentError, get_purchase_agent
from app.mcp_client import CatalogMcpClient, McpClientError


SCHEMA = """
CREATE TABLE IF NOT EXISTS requisicoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero BIGSERIAL UNIQUE NOT NULL,
    pedido_original TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'criada' CHECK (status = 'criada'),
    valor_total NUMERIC(12, 2) NOT NULL CHECK (valor_total >= 0),
    criada_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS itens_requisicao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requisicao_id UUID NOT NULL REFERENCES requisicoes(id) ON DELETE CASCADE,
    produto_origem_id INTEGER NOT NULL CHECK (produto_origem_id > 0),
    titulo TEXT NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(12, 2) NOT NULL CHECK (preco_unitario >= 0),
    valor_total NUMERIC(12, 2) NOT NULL CHECK (valor_total >= 0)
);

CREATE INDEX IF NOT EXISTS itens_requisicao_requisicao_id_idx
    ON itens_requisicao (requisicao_id);
CREATE INDEX IF NOT EXISTS requisicoes_criada_em_idx
    ON requisicoes (criada_em DESC);
"""


def initialize_database() -> None:
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            cursor.execute(SCHEMA)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield

app = FastAPI(title="Purchase Agent API", lifespan=lifespan)


class PurchaseRequest(BaseModel):
    pedido: str = Field(min_length=1, max_length=2_000)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


@app.exception_handler(ApiError)
async def api_error(_: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"erro": {"codigo": error.code, "mensagem": error.message}})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/requisicoes", status_code=201)
async def create_purchase_request(payload: PurchaseRequest) -> dict[str, Any]:
    pedido = payload.pedido.strip()
    if not pedido:
        raise ApiError(422, "invalid_request", "O pedido não pode estar vazio.")
    catalog = CatalogMcpClient(os.environ["MCP_SERVER_URL"])
    try:
        decision = await get_purchase_agent().decide(pedido, catalog)
        items = await _validate_items(decision.itens, catalog, _price_limit(pedido))
    except McpClientError as error:
        raise ApiError(503, "catalog_unavailable", "Não foi possível consultar o catálogo agora. Tente novamente.") from error
    except AgentConfigurationError as error:
        raise ApiError(503, "agent_unavailable", "O agente não está disponível agora.") from error
    except AgentError as error:
        raise ApiError(422, "agent_result_invalid", "O agente não retornou uma compra válida.") from error

    total = sum((item["valor_total"] for item in items), Decimal("0"))
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO requisicoes (pedido_original, valor_total) VALUES (%s, %s) RETURNING id, numero, criada_em",
                (pedido, total),
            )
            requisicao_id, numero, criada_em = cursor.fetchone()
            for item in items:
                cursor.execute(
                    "INSERT INTO itens_requisicao (requisicao_id, produto_origem_id, titulo, quantidade, preco_unitario, valor_total) VALUES (%s, %s, %s, %s, %s, %s)",
                    (requisicao_id, item["produto_id"], item["titulo"], item["quantidade"], item["preco_unitario"], item["valor_total"]),
                )
    return {"requisicao": {"numero": numero, "pedido": pedido, "itens": [_public_item(item) for item in items], "valorTotal": float(total), "justificativa": decision.justificativa, "criadaEm": criada_em.isoformat()}}


@app.get("/requisicoes")
def list_purchase_requests() -> dict[str, Any]:
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT numero, pedido_original, status, valor_total, criada_em FROM requisicoes ORDER BY criada_em DESC")
            rows = cursor.fetchall()
    return {"requisicoes": [{"numero": row[0], "pedido": row[1], "status": row[2], "valorTotal": float(row[3]), "criadaEm": row[4].isoformat()} for row in rows]}


async def _validate_items(selected: list[Any], catalog: CatalogMcpClient, limit: Decimal | None) -> list[dict[str, Any]]:
    items = []
    for selected_item in selected:
        result = await catalog.call_tool("detalhar_produto", {"id": selected_item.produto_id})
        detail = _tool_json(result)
        price = Decimal(str(detail.get("preco")))
        if price < 0 or (limit is not None and price > limit):
            raise AgentError("Produto não é compatível com o teto informado")
        quantity = selected_item.quantidade
        items.append({"produto_id": detail["id"], "titulo": detail["titulo"], "quantidade": quantity, "preco_unitario": price, "valor_total": price * quantity})
    if not items:
        raise AgentError("Nenhum produto compatível foi encontrado")
    return items


def _tool_json(result: Any) -> dict[str, Any]:
    try:
        return json.loads(result.content[0].text)
    except (AttributeError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise AgentError("O catálogo retornou dados inválidos") from error


def _price_limit(pedido: str) -> Decimal | None:
    match = re.search(r"(?:US\$|\$)\s*([\d.,]+)\s*(?:cada|por unidade)?", pedido, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1)
    normalized = value.replace(".", "").replace(",", ".") if "," in value else value.replace(".", "")
    return Decimal(normalized)


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    return {"produtoId": item["produto_id"], "titulo": item["titulo"], "quantidade": item["quantidade"], "precoUnitario": float(item["preco_unitario"]), "valorTotal": float(item["valor_total"])}
