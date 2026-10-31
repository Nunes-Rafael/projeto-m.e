from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Catalog MCP Server")

CATALOG_URL = "https://dummyjson.com/products"
CATALOG_TIMEOUT_SECONDS = 3.0


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


@app.post("/tools/buscar_produtos")
async def buscar_produtos(input: SearchProductsInput) -> dict[str, list[dict[str, Any]]]:
    payload = await get_catalog("/search", {"q": input.termo})
    products = payload.get("products")
    if not isinstance(products, list) or not all(isinstance(product, dict) for product in products):
        raise catalog_error()
    return {"produtos": [normalize_product(product) for product in products]}


@app.post("/tools/detalhar_produto")
async def detalhar_produto(input: ProductDetailsInput) -> dict[str, Any]:
    product = await get_catalog(f"/{input.id}")
    normalized = normalize_product(product)
    normalized.update(
        {
            "descricao": product.get("description"),
            "estoque": product.get("stock"),
        }
    )
    return normalized
