import json
import os
from types import SimpleNamespace

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.agent import AgentDecision, AgentError, SelectedItem
from app.mcp_client import McpClientError
from app import main


class FakeAgent:
    def __init__(self, items: list[SelectedItem] | None = None, error: Exception | None = None):
        self.items = items or [SelectedItem(produto_id=78, quantidade=3)]
        self.error = error

    async def decide(self, _pedido, _catalog):
        if self.error:
            raise self.error
        return AgentDecision(itens=self.items, justificativa="Seleção de teste.")


class FakeCatalog:
    def __init__(self, _url):
        self.fail_on: int | None = None

    async def call_tool(self, _name, arguments):
        product_id = arguments["id"]
        if self.fail_on == product_id:
            raise McpClientError("catálogo indisponível")
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps({"id": product_id, "titulo": f"Laptop {product_id}", "preco": 1999.99}))])


@pytest.fixture(autouse=True)
def clean_database():
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
        connection.execute("TRUNCATE itens_requisicao, requisicoes RESTART IDENTITY")


@pytest.fixture
def client(monkeypatch):
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

    listing = test_client.get("/requisicoes")
    assert listing.status_code == 200
    assert listing.json()["requisicoes"][0]["numero"] == 1


def test_agent_failure_does_not_persist(client):
    test_client, agent, _ = client
    agent.error = AgentError("sem produto compatível")

    response = test_client.post("/requisicoes", json={"pedido": "Preciso de algo impossível."})

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
