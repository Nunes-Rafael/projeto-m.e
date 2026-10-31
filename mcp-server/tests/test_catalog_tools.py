import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.main import buscar_produtos, detalhar_produto, get_catalog


def test_search_returns_normalized_products() -> None:
    payload = {"products": [{"id": 10, "title": "Notebook de teste", "price": 999.99, "category": "laptops", "brand": "Example"}]}
    with patch("app.main.get_catalog", new=AsyncMock(return_value=payload)) as catalog:
        response = asyncio.run(buscar_produtos("laptop"))
    assert response["produtos"][0]["titulo"] == "Notebook de teste"
    catalog.assert_awaited_once_with("/search", {"q": "laptop"})


def test_product_details_returns_agent_fields() -> None:
    payload = {"id": 10, "title": "Notebook", "price": 999.99, "category": "laptops", "brand": "Example", "description": "Descrição", "stock": 12}
    with patch("app.main.get_catalog", new=AsyncMock(return_value=payload)):
        response = asyncio.run(detalhar_produto(10))
    assert response["descricao"] == "Descrição"
    assert response["estoque"] == 12


def test_invalid_input_is_rejected_without_catalog_call() -> None:
    with patch("app.main.get_catalog", new=AsyncMock()) as catalog:
        with pytest.raises(ValueError):
            asyncio.run(buscar_produtos(" "))
    catalog.assert_not_awaited()


@pytest.mark.parametrize("error", [httpx.TimeoutException("timeout"), httpx.HTTPStatusError("bad gateway", request=httpx.Request("GET", "https://catalog"), response=httpx.Response(502))])
def test_catalog_http_failures_return_safe_error(error: Exception) -> None:
    class FailingClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def get(self, *_args, **_kwargs): raise error

    with patch("app.main.httpx.AsyncClient", return_value=FailingClient()):
        with pytest.raises(HTTPException) as raised:
            asyncio.run(get_catalog("/search", {"q": "laptop"}))
    assert raised.value.status_code == 503
    assert raised.value.detail["codigo"] == "catalog_unavailable"


def test_invalid_catalog_payload_returns_safe_error() -> None:
    class InvalidPayloadClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def get(self, *_args, **_kwargs):
            return httpx.Response(200, json=["not", "a", "mapping"], request=httpx.Request("GET", "https://catalog"))

    with patch("app.main.httpx.AsyncClient", return_value=InvalidPayloadClient()):
        with pytest.raises(HTTPException) as raised:
            asyncio.run(get_catalog("/search", {"q": "laptop"}))
    assert raised.value.status_code == 503
