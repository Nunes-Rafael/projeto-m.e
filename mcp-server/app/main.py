from contextlib import asynccontextmanager
from decimal import Decimal
import hashlib
import hmac
import json
import os
import re
import secrets
from typing import Any
from uuid import UUID

import httpx
import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

mcp = FastMCP("catalog")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Catalog MCP Server", lifespan=lifespan)

CATALOG_URL = "https://dummyjson.com/products"
CATALOG_TIMEOUT_SECONDS = 3.0
MAX_REQUISITION_LINES = 20
MAX_QUANTITY = 100
MAX_MONEY = Decimal("9999999999.99")


class PersistenceError(Exception):
    pass


class IdempotencyConflict(PersistenceError):
    pass


class RequisitionItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    produto_origem_id: int = Field(gt=0, strict=True)
    titulo: str = Field(min_length=1, max_length=500)
    quantidade: int = Field(ge=1, le=MAX_QUANTITY, strict=True)
    preco_unitario: str
    valor_total: str


class CreateRequisitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chave_idempotencia: UUID
    pedido_original: str = Field(min_length=1, max_length=2_000)
    itens: list[RequisitionItemInput] = Field(min_length=1, max_length=MAX_REQUISITION_LINES)
    valor_total: str

    @field_validator("pedido_original")
    @classmethod
    def normalize_order(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("pedido vazio")
        return normalized

    @model_validator(mode="after")
    def validate_totals(self) -> "CreateRequisitionInput":
        ids = [item.produto_origem_id for item in self.itens]
        if len(ids) != len(set(ids)):
            raise ValueError("produtos duplicados")
        line_total = sum(
            (_money(item.valor_total) for item in self.itens), Decimal("0.00")
        )
        declared_total = _money(self.valor_total)
        if declared_total != line_total:
            raise ValueError("total inconsistente")
        for item in self.itens:
            if _money(item.valor_total) != _money(item.preco_unitario) * item.quantidade:
                raise ValueError("total de item inconsistente")
        if declared_total > MAX_MONEY:
            raise ValueError("total fora da faixa")
        return self


def _money(value: str) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,10}\.\d{2}", value):
        raise ValueError("valor monetário deve ter duas casas decimais")
    amount = Decimal(value)
    if amount > MAX_MONEY:
        raise ValueError("valor monetário fora da faixa")
    return amount


def normalize_requisition(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    parsed = CreateRequisitionInput.model_validate(payload)
    normalized_items = []
    for item in sorted(parsed.itens, key=lambda current: current.produto_origem_id):
        price = _money(item.preco_unitario)
        row_total = _money(item.valor_total)
        title = item.titulo.strip()
        if not title:
            raise ValueError("título vazio")
        normalized_items.append(
            {
                "produto_origem_id": item.produto_origem_id,
                "titulo": title,
                "quantidade": item.quantidade,
                "preco_unitario": f"{price:.2f}",
                "valor_total": f"{row_total:.2f}",
            }
        )
    normalized = {
        "chave_idempotencia": str(parsed.chave_idempotencia),
        "pedido_original": parsed.pedido_original,
        "itens": normalized_items,
        "valor_total": f"{_money(parsed.valor_total):.2f}",
    }
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return normalized, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def service_secret() -> str:
    return os.getenv("MCP_WRITE_TOKEN", "").strip()


def authenticate_service(configured: str, supplied_header: str) -> str:
    if not configured:
        return "unavailable"
    if not hmac.compare_digest(supplied_header, f"Bearer {configured}"):
        return "unauthorized"
    return "authorized"


@app.middleware("http")
async def authenticate_service_requests(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        configured = service_secret()
        supplied = request.headers.get("authorization", "")
        status = authenticate_service(configured, supplied)
        if status == "unavailable":
            return JSONResponse(status_code=503, content={"erro": {"codigo": "service_unavailable", "mensagem": "Serviço indisponível."}})
        if status != "authorized":
            return JSONResponse(status_code=401, content={"erro": {"codigo": "unauthorized", "mensagem": "Não autorizado."}})
    return await call_next(request)


class SearchProductsInput(BaseModel):
    termo: str = Field(min_length=2, max_length=120)

    @field_validator("termo")
    @classmethod
    def normalize_term(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("termo deve ter entre 2 e 120 caracteres")
        return normalized


class ProductDetailsInput(BaseModel):
    id: int = Field(gt=0)


def catalog_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "codigo": "catalog_unavailable",
            "mensagem": "Não foi possível consultar o catálogo agora. Tente novamente.",
        },
    )


async def get_catalog(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=CATALOG_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{CATALOG_URL}{path}", params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        raise catalog_error() from None

    if not isinstance(payload, dict):
        raise catalog_error()
    return payload


def normalize_product(product: dict[str, Any]) -> dict[str, Any]:
    product_id = product.get("id")
    title = product.get("title")
    price = product.get("price")
    if not isinstance(product_id, int) or not isinstance(title, str) or not isinstance(price, (int, float)):
        raise catalog_error()

    return {
        "id": product_id,
        "titulo": title,
        "preco": price,
        "categoria": product.get("category"),
        "marca": product.get("brand"),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@mcp.tool()
async def buscar_produtos(termo: str) -> dict[str, list[dict[str, Any]]]:
    input = SearchProductsInput(termo=termo)
    payload = await get_catalog("/search", {"q": input.termo})
    products = payload.get("products")
    if not isinstance(products, list) or not all(isinstance(product, dict) for product in products):
        raise catalog_error()
    return {"produtos": [normalize_product(product) for product in products]}


@mcp.tool()
async def detalhar_produto(id: int) -> dict[str, Any]:
    input = ProductDetailsInput(id=id)
    product = await get_catalog(f"/{input.id}")
    normalized = normalize_product(product)
    normalized.update(
        {
            "descricao": product.get("description"),
            "estoque": product.get("stock"),
        }
    )
    return normalized


def persist_requisition(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized, payload_hash = normalize_requisition(payload)
    except ValidationError:
        return {"erro": {"codigo": "invalid_requisition", "mensagem": "Dados da requisição inválidos."}}
    except ValueError:
        return {"erro": {"codigo": "invalid_requisition", "mensagem": "Dados da requisição inválidos."}}

    database_url = os.getenv("MCP_DATABASE_URL", "").strip()
    if not database_url:
        return {"erro": {"codigo": "persistence_unavailable", "mensagem": "Persistência indisponível."}}

    key = normalized["chave_idempotencia"]
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO requisicoes (chave_idempotencia, hash_payload, pedido_original, valor_total)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (chave_idempotencia) DO NOTHING
                RETURNING id, numero, criada_em
                """,
                (key, payload_hash, normalized["pedido_original"], normalized["valor_total"]),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    "SELECT id, numero, criada_em, hash_payload FROM requisicoes WHERE chave_idempotencia = %s",
                    (key,),
                )
                existing = cursor.fetchone()
                if existing is None:
                    return {"erro": {"codigo": "persistence_unavailable", "mensagem": "Persistência indisponível."}}
                if not hmac.compare_digest(existing[3], payload_hash):
                    return {"erro": {"codigo": "idempotency_conflict", "mensagem": "Chave de idempotência reutilizada com dados diferentes."}}
                requisition_id, number, created_at = existing[:3]
            else:
                requisition_id, number, created_at = row
                for item in normalized["itens"]:
                    cursor.execute(
                        """
                        INSERT INTO itens_requisicao
                            (requisicao_id, produto_origem_id, titulo, quantidade, preco_unitario, valor_total)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            requisition_id,
                            item["produto_origem_id"],
                            item["titulo"],
                            item["quantidade"],
                            item["preco_unitario"],
                            item["valor_total"],
                        ),
                    )
            cursor.execute(
                """
                SELECT produto_origem_id, titulo, quantidade, preco_unitario, valor_total
                FROM itens_requisicao WHERE requisicao_id = %s ORDER BY produto_origem_id
                """,
                (requisition_id,),
            )
            persisted_items = cursor.fetchall()

    return {
        "requisicao": {
            "numero": number,
            "pedido": normalized["pedido_original"],
            "itens": [
                {
                    "produtoId": item[0],
                    "titulo": item[1],
                    "quantidade": item[2],
                    "precoUnitario": float(item[3]),
                    "valorTotal": float(item[4]),
                }
                for item in persisted_items
            ],
            "valorTotal": float(Decimal(normalized["valor_total"])),
            "criadaEm": created_at.isoformat(),
        }
    }


@mcp.tool()
async def criar_requisicao(
    chave_idempotencia: str,
    pedido_original: str,
    itens: list[dict[str, Any]],
    valor_total: str,
) -> dict[str, Any]:
    """Persiste um pedido canônico encaminhado pelo backend autenticado."""
    try:
        return persist_requisition(
            {
                "chave_idempotencia": chave_idempotencia,
                "pedido_original": pedido_original,
                "itens": itens,
                "valor_total": valor_total,
            }
        )
    except Exception:
        return {"erro": {"codigo": "persistence_unavailable", "mensagem": "Persistência indisponível."}}


app.mount("/", mcp.streamable_http_app())
