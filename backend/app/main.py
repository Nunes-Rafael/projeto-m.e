import os
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import uuid4

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pydantic import ConfigDict, ValidationError

from app.agent import AgentConfigurationError, AgentError, AgentPersistenceError, AgentProviderError, NoCompatibleProductError, get_purchase_agent
from app.mcp_client import ALLOWED_TOOLS, CatalogMcpClient, McpClientError


app = FastAPI(title="Purchase Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class PurchaseRequest(BaseModel):
    pedido: str = Field(min_length=1, max_length=2_000)


class RequisitionIntentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    produto_id: int = Field(gt=0, strict=True)
    quantidade: int = Field(ge=1, le=100, strict=True)


class RequisitionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    itens: list[RequisitionIntentItem] = Field(min_length=1, max_length=20)
    justificativa: str = Field(default="", max_length=1_000)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


class ExecutionCatalog:
    def __init__(self, client: CatalogMcpClient, pedido: str, limit: Decimal | None) -> None:
        self.client = client
        self.pedido = pedido
        self.limit = limit
        self.searched_product_ids: set[int] = set()
        self.tools_called: list[str] = []
        self.idempotency_key = str(uuid4())
        self.persisted_requisition: dict[str, Any] | None = None

    @property
    def has_candidates(self) -> bool:
        return bool(self.searched_product_ids)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "criar_requisicao":
            return await self._create_requisition(arguments)
        if name not in ALLOWED_TOOLS:
            raise AgentError("Ferramenta MCP não permitida")
        result = await self.client.call_tool(name, arguments)
        if name in ALLOWED_TOOLS and name not in self.tools_called:
            self.tools_called.append(name)
        if name == "buscar_produtos":
            products = _tool_json(result).get("produtos", [])
            self.searched_product_ids.update(product["id"] for product in products if type(product.get("id")) is int)
        return result

    async def _create_requisition(self, arguments: dict[str, Any]) -> Any:
        if self.persisted_requisition is not None:
            return _tool_result({"requisicao": self.persisted_requisition})
        try:
            intent = RequisitionIntent.model_validate(arguments)
        except ValidationError as error:
            raise AgentError("A intenção de gravação é inválida") from error
        product_ids = [item.produto_id for item in intent.itens]
        if len(product_ids) != len(set(product_ids)):
            raise AgentError("A intenção contém produtos duplicados")
        if len(product_ids) > 20:
            raise AgentError("A intenção excede o limite de itens")
        if any(product_id not in self.searched_product_ids for product_id in product_ids):
            raise AgentError("A intenção contém produto sem proveniência nesta execução")
        if self.limit is not None and (not self.limit.is_finite() or self.limit < 0):
            raise AgentError("O teto informado é inválido")

        canonical_items = []
        for selected in intent.itens:
            result = await self.call_tool("detalhar_produto", {"id": selected.produto_id})
            detail = _tool_json(result)
            if detail.get("id") != selected.produto_id:
                raise AgentError("O catálogo retornou um produto diferente do solicitado")
            if not isinstance(detail.get("titulo"), str) or not detail["titulo"].strip():
                raise AgentError("O catálogo retornou um título inválido")
            try:
                price = Decimal(str(detail["preco"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except (KeyError, InvalidOperation, ValueError) as error:
                raise AgentError("O catálogo retornou um preço inválido") from error
            if not price.is_finite() or price < 0 or price > Decimal("9999999999.99"):
                raise AgentError("O preço retornado está fora dos limites")
            if self.limit is not None and price > self.limit:
                raise NoCompatibleProductError("Produto não é compatível com o teto informado")
            row_total = (price * selected.quantidade).quantize(Decimal("0.01"))
            if row_total > Decimal("9999999999.99"):
                raise AgentError("O total do item excede o limite")
            canonical_items.append(
                {
                    "produto_origem_id": selected.produto_id,
                    "titulo": detail["titulo"].strip(),
                    "quantidade": selected.quantidade,
                    "preco_unitario": f"{price:.2f}",
                    "valor_total": f"{row_total:.2f}",
                }
            )
        total = sum((Decimal(item["valor_total"]) for item in canonical_items), Decimal("0.00"))
        if total > Decimal("9999999999.99"):
            raise AgentError("O total da requisição excede o limite")
        payload = {
            "chave_idempotencia": self.idempotency_key,
            "pedido_original": self.pedido,
            "itens": canonical_items,
            "valor_total": f"{total:.2f}",
        }
        try:
            result = await self.client.create_requisition(payload)
        except McpClientError as error:
            raise AgentPersistenceError("A persistência não está disponível") from error
        response = _tool_json(result)
        error = response.get("erro")
        if error:
            if error.get("codigo") == "idempotency_conflict":
                raise AgentPersistenceError("A chave de idempotência já foi usada com outro conteúdo")
            if error.get("codigo") == "invalid_requisition":
                raise AgentError("O servidor MCP rejeitou o contrato canônico")
            raise AgentPersistenceError("A persistência não está disponível")
        requisition = response.get("requisicao")
        if not isinstance(requisition, dict) or not isinstance(requisition.get("numero"), int):
            raise AgentPersistenceError("A persistência não confirmou a requisição")
        self.persisted_requisition = requisition
        if "criar_requisicao" not in self.tools_called:
            self.tools_called.append("criar_requisicao")
        return result


def _tool_result(value: dict[str, Any]) -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(value))])


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
    catalog = ExecutionCatalog(CatalogMcpClient(os.environ["MCP_SERVER_URL"]), pedido, _price_limit(pedido))
    try:
        decision = await get_purchase_agent().decide(pedido, catalog)
        if catalog.persisted_requisition is None:
            raise AgentError("O agente não confirmou a intenção de gravação")
    except McpClientError as error:
        raise ApiError(503, "catalog_unavailable", "Não foi possível consultar o catálogo agora. Tente novamente.") from error
    except AgentConfigurationError as error:
        raise ApiError(503, "agent_unavailable", "O agente não está disponível agora.") from error
    except AgentProviderError as error:
        if error.reason == "key_limit_exceeded":
            raise ApiError(503, "provider_key_limit_exceeded", "O limite de uso desta chave OpenRouter foi atingido. Aumente o limite da chave ou configure outra.") from error
        raise ApiError(503, "agent_provider_unavailable", "O provedor do agente está indisponível ou recusou a solicitação. Confira a chave e o modelo configurados.") from error
    except NoCompatibleProductError as error:
        raise ApiError(422, "no_compatible_product", "Nenhum produto atende aos requisitos do pedido.") from error
    except AgentPersistenceError as error:
        raise ApiError(503, "persistence_unavailable", "Não foi possível registrar a requisição agora. Tente novamente.") from error
    except AgentError as error:
        raise ApiError(422, "agent_result_invalid", "O agente não retornou uma compra válida.") from error

    requisition = catalog.persisted_requisition
    return {
        "requisicao": {
            **requisition,
            "justificativa": decision.justificativa,
            "ferramentasChamadas": catalog.tools_called,
        }
    }


@app.get("/requisicoes")
def list_purchase_requests() -> dict[str, Any]:
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT numero, pedido_original, status, valor_total, criada_em FROM requisicoes ORDER BY criada_em DESC")
            rows = cursor.fetchall()
    return {"requisicoes": [{"numero": row[0], "pedido": row[1], "status": row[2], "valorTotal": float(row[3]), "criadaEm": row[4].isoformat()} for row in rows]}


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
    if "." in value and "," in value:
        decimal_separator = "." if value.rfind(".") > value.rfind(",") else ","
        thousands_separator = "," if decimal_separator == "." else "."
        normalized = value.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif "," in value:
        whole, fraction = value.rsplit(",", 1)
        normalized = whole.replace(".", "").replace(",", "") + (f".{fraction}" if len(fraction) != 3 else fraction)
    elif "." in value:
        whole, fraction = value.rsplit(".", 1)
        normalized = whole.replace(".", "") + (f".{fraction}" if len(fraction) != 3 else fraction)
    else:
        normalized = value
    try:
        amount = Decimal(normalized)
    except InvalidOperation as error:
        raise ApiError(422, "invalid_request", "O limite informado não é válido.") from error
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
