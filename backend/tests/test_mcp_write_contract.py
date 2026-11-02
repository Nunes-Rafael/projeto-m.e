import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agent import AgentError, NoCompatibleProductError
from app.main import ExecutionCatalog
from app.agent import _tool_schemas
from app.mcp_client import ALLOWED_TOOLS, CatalogMcpClient, McpClientError


def tool_result(payload):
    return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])


class FakeMcpClient:
    def __init__(self, products):
        self.products = products
        self.writes = []

    async def call_tool(self, name, arguments):
        if name == "buscar_produtos":
            return tool_result({"produtos": [{"id": product_id} for product_id in self.products]})
        product = self.products[arguments["id"]]
        return tool_result({"id": arguments["id"], **product})

    async def create_requisition(self, payload):
        self.writes.append(payload)
        return tool_result(
            {
                "requisicao": {
                    "numero": 1,
                    "pedido": payload["pedido_original"],
                    "itens": [
                        {
                            "produtoId": item["produto_origem_id"],
                            "titulo": item["titulo"],
                            "quantidade": item["quantidade"],
                            "precoUnitario": float(item["preco_unitario"]),
                            "valorTotal": float(item["valor_total"]),
                        }
                        for item in payload["itens"]
                    ],
                    "valorTotal": float(payload["valor_total"]),
                    "criadaEm": "2026-01-01T00:00:00+00:00",
                }
            }
        )


def test_backend_revalidates_provenance_and_rebuilds_financial_payload():
    client = FakeMcpClient({1: {"titulo": "Notebook", "preco": "1250.00"}})
    execution = ExecutionCatalog(client, "Preciso de 2 notebooks até $1,500 each.", None)
    asyncio.run(execution.call_tool("buscar_produtos", {"termo": "notebook"}))
    asyncio.run(
        execution.call_tool(
            "criar_requisicao",
            {
                "itens": [{"produto_id": 1, "quantidade": 2}],
                "justificativa": "Atende ao pedido.",
            },
        )
    )

    payload = client.writes[0]
    assert payload["pedido_original"] == "Preciso de 2 notebooks até $1,500 each."
    assert payload["itens"][0]["preco_unitario"] == "1250.00"
    assert payload["itens"][0]["valor_total"] == "2500.00"
    assert payload["valor_total"] == "2500.00"
    assert execution.persisted_requisition["numero"] == 1
    assert execution.tools_called == ["buscar_produtos", "detalhar_produto", "criar_requisicao"]


def test_backend_rejects_product_without_search_provenance():
    client = FakeMcpClient({1: {"titulo": "Notebook", "preco": "1250.00"}})
    execution = ExecutionCatalog(client, "Notebook", None)
    with pytest.raises(AgentError):
        asyncio.run(
            execution.call_tool(
                "criar_requisicao",
                {"itens": [{"produto_id": 1, "quantidade": 1}]},
            )
        )
    assert client.writes == []


def test_backend_rejects_quantity_and_duplicate_ids():
    client = FakeMcpClient({1: {"titulo": "Notebook", "preco": "1250.00"}})
    execution = ExecutionCatalog(client, "Notebook", None)
    asyncio.run(execution.call_tool("buscar_produtos", {"termo": "notebook"}))
    for items in (
        [{"produto_id": 1, "quantidade": 101}],
        [{"produto_id": 1, "quantidade": 1}, {"produto_id": 1, "quantidade": 2}],
    ):
        with pytest.raises(AgentError):
            asyncio.run(execution.call_tool("criar_requisicao", {"itens": items}))
    assert client.writes == []


def test_backend_rejects_price_over_order_limit_without_write():
    client = FakeMcpClient({1: {"titulo": "Notebook", "preco": "1999.99"}})
    execution = ExecutionCatalog(client, "Notebook até US$ 1,500", Decimal("1500.00"))
    asyncio.run(execution.call_tool("buscar_produtos", {"termo": "notebook"}))
    with pytest.raises(NoCompatibleProductError):
        asyncio.run(execution.call_tool("criar_requisicao", {"itens": [{"produto_id": 1, "quantidade": 1}]}))
    assert client.writes == []


def test_repeat_create_intent_in_same_execution_returns_cached_result():
    client = FakeMcpClient({1: {"titulo": "Notebook", "preco": "1250.00"}})
    execution = ExecutionCatalog(client, "Notebook", None)
    asyncio.run(execution.call_tool("buscar_produtos", {"termo": "notebook"}))
    intent = {"itens": [{"produto_id": 1, "quantidade": 1}]}
    first = asyncio.run(execution.call_tool("criar_requisicao", intent))
    second = asyncio.run(execution.call_tool("criar_requisicao", intent))
    assert first.content[0].text == second.content[0].text
    assert len(client.writes) == 1


def test_write_tool_is_not_directly_allowlisted_or_callable_without_service_secret(monkeypatch):
    monkeypatch.delenv("MCP_WRITE_TOKEN", raising=False)
    client = CatalogMcpClient("http://mcp-server:8001")
    assert "criar_requisicao" not in ALLOWED_TOOLS
    with pytest.raises(McpClientError):
        asyncio.run(client.call_tool("criar_requisicao", {}))
    with pytest.raises(McpClientError):
        asyncio.run(client.create_requisition({}))


def test_model_only_receives_write_intent_schema_after_search():
    assert all(schema["function"]["name"] != "criar_requisicao" for schema in _tool_schemas())
    assert any(schema["function"]["name"] == "criar_requisicao" for schema in _tool_schemas(True))
