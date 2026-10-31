from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_search_returns_normalized_products() -> None:
    payload = {
        "products": [
            {
                "id": 10,
                "title": "Notebook de teste",
                "price": 999.99,
                "category": "laptops",
                "brand": "Example",
                "description": "Não deve aparecer na busca",
            }
        ]
    }

    with patch("app.main.get_catalog", new=AsyncMock(return_value=payload)) as get_catalog:
        response = client.post("/tools/buscar_produtos", json={"termo": "laptop"})

    assert response.status_code == 200
    assert response.json() == {
        "produtos": [
            {
                "id": 10,
                "titulo": "Notebook de teste",
                "preco": 999.99,
                "categoria": "laptops",
                "marca": "Example",
            }
        ]
    }
    get_catalog.assert_awaited_once_with("/search", {"q": "laptop"})


def test_product_details_returns_agent_fields() -> None:
    payload = {
        "id": 10,
        "title": "Notebook de teste",
        "price": 999.99,
        "category": "laptops",
        "brand": "Example",
        "description": "Descrição do produto",
        "stock": 12,
    }

    with patch("app.main.get_catalog", new=AsyncMock(return_value=payload)) as get_catalog:
        response = client.post("/tools/detalhar_produto", json={"id": 10})

    assert response.status_code == 200
    assert response.json()["descricao"] == "Descrição do produto"
    assert response.json()["estoque"] == 12
    get_catalog.assert_awaited_once_with("/10")


def test_invalid_input_is_rejected_without_catalog_call() -> None:
    with patch("app.main.get_catalog", new=AsyncMock()) as get_catalog:
        response = client.post("/tools/buscar_produtos", json={"termo": " "})

    assert response.status_code == 422
    get_catalog.assert_not_awaited()


def test_catalog_timeout_returns_safe_error() -> None:
    class TimedOutClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            import httpx

            raise httpx.TimeoutException("network details")

    with patch("app.main.httpx.AsyncClient", return_value=TimedOutClient()):
        response = client.post("/tools/buscar_produtos", json={"termo": "laptop"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "codigo": "catalog_unavailable",
            "mensagem": "Não foi possível consultar o catálogo agora. Tente novamente.",
        }
    }
