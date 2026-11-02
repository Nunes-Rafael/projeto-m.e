import asyncio
import hashlib
import json
import os
import secrets
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.agent import AgentDecision, AgentError, NoCompatibleProductError, SelectedItem
from app.mcp_client import McpClientError
from app import main


class FakeAgent:
    def __init__(self, items: list[SelectedItem] | None = None, error: Exception | None = None):
        self.items = items or [SelectedItem(produto_id=78, quantidade=3)]
        self.error = error
        self.fail_after_search = False

    async def decide(self, _pedido, catalog):
        if self.error:
            raise self.error
        await catalog.call_tool("buscar_produtos", {"termo": "laptop"})
        if self.fail_after_search:
            raise AgentError("falha depois da busca")
        await catalog.call_tool(
            "criar_requisicao",
            {
                "itens": [item.model_dump() | {"produto_id": item.produto_id} for item in self.items],
                "justificativa": "Seleção de teste.",
            },
        )
        return AgentDecision(itens=self.items, justificativa="Seleção de teste.")


class FakeCatalog:
    def __init__(self, _url):
        self.fail_on: int | None = None

    async def call_tool(self, name, arguments):
        if name == "buscar_produtos":
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps({"produtos": [{"id": 78}, {"id": 79}]}))])
        product_id = arguments["id"]
        if self.fail_on == product_id:
            raise McpClientError("catálogo indisponível")
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps({"id": product_id, "titulo": f"Laptop {product_id}", "preco": 1999.99}))])

    async def create_requisition(self, payload):
        writer_url = os.environ["MCP_TEST_WRITER_DATABASE_URL"]
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with psycopg.connect(writer_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO requisicoes (chave_idempotencia, hash_payload, pedido_original, valor_total) VALUES (%s, %s, %s, %s) ON CONFLICT (chave_idempotencia) DO NOTHING RETURNING id, numero, criada_em",
                    (payload["chave_idempotencia"], payload_hash, payload["pedido_original"], payload["valor_total"]),
                )
                row = cursor.fetchone()
                if row is None:
                    cursor.execute(
                        "SELECT id, numero, criada_em, hash_payload FROM requisicoes WHERE chave_idempotencia = %s",
                        (payload["chave_idempotencia"],),
                    )
                    existing = cursor.fetchone()
                    if existing[3] != payload_hash:
                        return _tool_result({"erro": {"codigo": "idempotency_conflict"}})
                    request_id, number, created_at = existing[:3]
                else:
                    request_id, number, created_at = row
                    for item in payload["itens"]:
                        cursor.execute(
                            "INSERT INTO itens_requisicao (requisicao_id, produto_origem_id, titulo, quantidade, preco_unitario, valor_total) VALUES (%s, %s, %s, %s, %s, %s)",
                            (request_id, item["produto_origem_id"], item["titulo"], item["quantidade"], item["preco_unitario"], item["valor_total"]),
                        )
                cursor.execute(
                    "SELECT produto_origem_id, titulo, quantidade, preco_unitario, valor_total FROM itens_requisicao WHERE requisicao_id = %s ORDER BY produto_origem_id",
                    (request_id,),
                )
                items = cursor.fetchall()
        return _tool_result(
            {
                "requisicao": {
                    "numero": number,
                    "pedido": payload["pedido_original"],
                    "itens": [
                        {"produtoId": item[0], "titulo": item[1], "quantidade": item[2], "precoUnitario": float(item[3]), "valorTotal": float(item[4])}
                        for item in items
                    ],
                    "valorTotal": float(payload["valor_total"]),
                    "criadaEm": created_at.isoformat(),
                }
            }
        )


def _tool_result(payload):
    return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])


@pytest.fixture
def test_database(monkeypatch):
    owner_url = os.getenv("MIGRATION_TEST_DATABASE_URL", "").strip()
    if not owner_url:
        pytest.skip("Defina MIGRATION_TEST_DATABASE_URL para um banco exclusivo *_test")
    database_name = conninfo_to_dict(owner_url).get("dbname", "")
    if not database_name.endswith("_test"):
        pytest.fail("MIGRATION_TEST_DATABASE_URL deve usar banco exclusivo com sufixo _test")
    suffix = uuid4().hex[:10]
    api_role = f"api_test_{suffix}"
    mcp_role = f"mcp_test_{suffix}"
    monkeypatch.setenv("MIGRATION_DATABASE_URL", owner_url)
    monkeypatch.setenv("POSTGRES_DB", database_name)
    monkeypatch.setenv("PURCHASE_API_DB_USER", api_role)
    monkeypatch.setenv("PURCHASE_API_DB_PASSWORD", secrets.token_hex(32))
    monkeypatch.setenv("MCP_DB_USER", mcp_role)
    mcp_password = secrets.token_hex(32)
    monkeypatch.setenv("MCP_DB_PASSWORD", mcp_password)

    from app.migrate import migrate

    migrate()
    api_url = make_conninfo(owner_url, user=api_role, password=os.environ["PURCHASE_API_DB_PASSWORD"])
    writer_url = make_conninfo(owner_url, user=mcp_role, password=mcp_password)
    monkeypatch.setenv("DATABASE_URL", api_url)
    monkeypatch.setenv("MCP_TEST_WRITER_DATABASE_URL", writer_url)
    monkeypatch.setenv("MCP_SERVER_URL", "http://mcp-server:8001")
    with psycopg.connect(owner_url, autocommit=True) as connection:
        connection.execute("TRUNCATE itens_requisicao, requisicoes RESTART IDENTITY")
    try:
        yield
    finally:
        with psycopg.connect(owner_url, autocommit=True) as connection:
            connection.execute("TRUNCATE itens_requisicao, requisicoes RESTART IDENTITY")
            for role_name in (api_role, mcp_role):
                role = sql.Identifier(role_name)
                connection.execute(sql.SQL("DROP OWNED BY {}").format(role))
                connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(role))


@pytest.fixture
def client(monkeypatch, test_database):
    catalog = FakeCatalog("")
    agent = FakeAgent()
    monkeypatch.setattr(main, "CatalogMcpClient", lambda _url: catalog)
    monkeypatch.setattr(main, "get_purchase_agent", lambda: agent)
    with TestClient(main.app) as test_client:
        yield test_client, agent, catalog


def test_create_and_list_requisition(client):
    test_client, _, _ = client
    response = test_client.post("/requisicoes", json={"pedido": "Preciso de 3 laptops até US$ 2.000 cada."})

    assert response.status_code == 201
    requisicao = response.json()["requisicao"]
    assert requisicao["numero"] == 1
    assert requisicao["valorTotal"] == 5999.97
    assert requisicao["itens"][0]["quantidade"] == 3
    assert requisicao["ferramentasChamadas"] == ["buscar_produtos", "detalhar_produto", "criar_requisicao"]
    assert "arguments" not in requisicao
    assert "tool_call_id" not in requisicao

    listing = test_client.get("/requisicoes")
    assert listing.status_code == 200
    assert listing.json()["requisicoes"][0]["numero"] == 1


def test_agent_failure_does_not_persist(client):
    test_client, agent, _ = client
    agent.error = AgentError("sem produto compatível")

    response = test_client.post("/requisicoes", json={"pedido": "Preciso de algo impossível."})

    assert response.status_code == 422
    assert response.json()["erro"]["codigo"] == "agent_result_invalid"
    assert "ferramentasChamadas" not in response.json()
    assert test_client.get("/requisicoes").json()["requisicoes"] == []


def test_failure_after_tool_call_does_not_return_stale_telemetry(client):
    test_client, agent, _ = client
    agent.fail_after_search = True

    failed = test_client.post("/requisicoes", json={"pedido": "Preciso de um laptop."})
    assert failed.status_code == 422
    assert "ferramentasChamadas" not in failed.json()

    agent.fail_after_search = False
    successful = test_client.post("/requisicoes", json={"pedido": "Preciso de um laptop."})
    assert successful.status_code == 201
    assert successful.json()["requisicao"]["ferramentasChamadas"] == ["buscar_produtos", "detalhar_produto", "criar_requisicao"]


def test_execution_catalog_reports_one_tool_and_deduplicates_names():
    fake_catalog = FakeCatalog("")
    execution = main.ExecutionCatalog(fake_catalog, "pedido de teste", None)
    assert execution.tools_called == []

    asyncio.run(execution.call_tool("buscar_produtos", {"termo": "laptop"}))
    asyncio.run(execution.call_tool("buscar_produtos", {"termo": "notebook"}))

    assert execution.tools_called == ["buscar_produtos"]


def test_execution_catalog_does_not_report_failed_tool():
    fake_catalog = FakeCatalog("")
    fake_catalog.fail_on = 78
    execution = main.ExecutionCatalog(fake_catalog, "pedido de teste", None)

    asyncio.run(execution.call_tool("buscar_produtos", {"termo": "laptop"}))
    with pytest.raises(McpClientError):
        asyncio.run(execution.call_tool("detalhar_produto", {"id": 78}))

    assert execution.tools_called == ["buscar_produtos"]


def test_no_compatible_product_does_not_persist(client):
    test_client, agent, _ = client
    agent.error = NoCompatibleProductError("sem produto compatível")

    response = test_client.post("/requisicoes", json={"pedido": "Preciso de algo impossível."})

    assert response.status_code == 422
    assert response.json()["erro"]["codigo"] == "no_compatible_product"
    assert test_client.get("/requisicoes").json()["requisicoes"] == []


def test_item_not_returned_by_search_does_not_persist(client):
    test_client, agent, _ = client
    agent.items = [SelectedItem(produto_id=999, quantidade=1)]

    response = test_client.post("/requisicoes", json={"pedido": "Preciso de um laptop."})

    assert response.status_code == 422
    assert response.json()["erro"]["codigo"] == "agent_result_invalid"
    assert test_client.get("/requisicoes").json()["requisicoes"] == []


def test_catalog_failure_does_not_persist(client):
    test_client, _, catalog = client
    catalog.fail_on = 78

    response = test_client.post("/requisicoes", json={"pedido": "Preciso de 3 laptops."})

    assert response.status_code == 503
    assert response.json()["erro"]["codigo"] == "catalog_unavailable"
    assert test_client.get("/requisicoes").json()["requisicoes"] == []


def test_catalog_failure_after_first_item_does_not_persist(client):
    test_client, agent, catalog = client
    agent.items = [SelectedItem(produto_id=78, quantidade=1), SelectedItem(produto_id=79, quantidade=1)]
    catalog.fail_on = 79

    response = test_client.post("/requisicoes", json={"pedido": "Preciso de dois laptops."})

    assert response.status_code == 503
    assert test_client.get("/requisicoes").json()["requisicoes"] == []
