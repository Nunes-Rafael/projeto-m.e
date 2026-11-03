from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app import main
from app.agent import AgentDecision, NoCompatibleProductError, SelectedItem
from app.mcp_client import McpClientError


@dataclass(frozen=True)
class Product:
    id: int
    title: str
    category: str
    price: Decimal


PRODUCTS = {
    1: Product(1, "Notebook leve", "laptops", Decimal("1250.00")),
    2: Product(2, "Notebook premium", "laptops", Decimal("2400.00")),
    3: Product(3, "Monitor 27 polegadas", "monitors", Decimal("320.00")),
}


class MemoryDatabase:
    """Small in-memory store standing in for the MCP persistence service."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []

class FixtureCatalog:
    def __init__(self, products: dict[int, Product], database: MemoryDatabase, unavailable: bool = False) -> None:
        self.products = products
        self.database = database
        self.unavailable = unavailable
        self.writer_calls = 0

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if self.unavailable:
            raise McpClientError("fixture catalog unavailable")
        if name == "buscar_produtos":
            term = arguments["termo"].casefold()
            found = [p for p in self.products.values() if term in p.category or term in p.title.casefold()]
            return _tool_result({"produtos": [{"id": p.id} for p in found]})
        product = self.products[arguments["id"]]
        return _tool_result({"id": product.id, "titulo": product.title, "preco": str(product.price)})

    async def create_requisition(self, payload: dict[str, Any]) -> Any:
        self.writer_calls += 1
        total = sum((Decimal(item["valor_total"]) for item in payload["itens"]), Decimal("0.00"))
        if total != Decimal(payload["valor_total"]):
            return _tool_result({"erro": {"codigo": "invalid_requisition"}})
        number = len(self.database.requests) + 1
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        items = [
            {
                "produtoId": item["produto_origem_id"],
                "titulo": item["titulo"],
                "quantidade": item["quantidade"],
                "precoUnitario": float(item["preco_unitario"]),
                "valorTotal": float(item["valor_total"]),
            }
            for item in payload["itens"]
        ]
        requisition = {
            "numero": number,
            "pedido": payload["pedido_original"],
            "itens": items,
            "valorTotal": float(total),
            "criadaEm": created.isoformat(),
        }
        self.database.requests.append(requisition)
        self.database.items.extend(items)
        return _tool_result({"requisicao": requisition})


class FixtureAgent:
    def __init__(self, product_id: int | None, quantity: int = 1, no_result: bool = False) -> None:
        self.product_id = product_id
        self.quantity = quantity
        self.no_result = no_result

    async def decide(self, pedido: str, catalog: FixtureCatalog) -> AgentDecision:
        if self.no_result:
            term = "produto-inexistente"
        else:
            term = "laptops" if "notebook" in pedido.casefold() or "computador portátil" in pedido.casefold() else "monitors"
        result = await catalog.call_tool("buscar_produtos", {"termo": term})
        products = json.loads(result.content[0].text)["produtos"]
        if not products:
            raise NoCompatibleProductError("Nenhum produto compatível foi encontrado")
        intent = {
            "itens": [{"produto_id": self.product_id or products[0]["id"], "quantidade": self.quantity}],
            "justificativa": "Seleção determinística de fixture.",
        }
        await catalog.call_tool("criar_requisicao", intent)
        return AgentDecision(
            itens=[SelectedItem(produto_id=intent["itens"][0]["produto_id"], quantidade=self.quantity)],
            justificativa=intent["justificativa"],
        )


@dataclass(frozen=True)
class Scenario:
    name: str
    pedido: str
    product_id: int | None
    quantity: int
    expected_status: int
    expected_code: str | None
    rule: str
    unavailable: bool = False
    no_result: bool = False


SCENARIOS = (
    Scenario("sucesso com teto e quantidade", "Preciso de 2 notebooks até US$ 1.500 cada.", 1, 2, 201, None,
             "produto dentro do teto, quantidade 2 e total recalculado"),
    Scenario("termo alternativo compatível", "Preciso de um computador portátil abaixo de US$ 1.500.", 1, 1, 201, None,
             "termo alternativo encontra produto da categoria laptops dentro do teto"),
    Scenario("produto acima do teto", "Preciso de 1 notebook até US$ 1.500 cada.", 2, 1, 422, "no_compatible_product",
             "preço unitário acima do teto é rejeitado sem persistência"),
    Scenario("busca sem resultado", "Preciso de um produto inexistente.", None, 1, 422, "no_compatible_product",
             "nenhum candidato resulta em erro de domínio sem persistência", no_result=True),
    Scenario("falha recuperável do catálogo", "Preciso de um monitor.", 3, 1, 503, "catalog_unavailable",
             "indisponibilidade do catálogo resulta em erro recuperável sem persistência", unavailable=True),
)


def _tool_result(value: dict[str, Any]) -> Any:
    return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(value))])


def run_scenario(scenario: Scenario) -> tuple[bool, str]:
    database = MemoryDatabase()
    agent = FixtureAgent(scenario.product_id, scenario.quantity, scenario.no_result)
    catalog = FixtureCatalog(PRODUCTS, database, scenario.unavailable)
    original_connect = main.psycopg.connect
    original_catalog = main.CatalogMcpClient
    original_agent = main.get_purchase_agent
    original_mcp_url = os.environ.get("MCP_SERVER_URL")
    try:
        os.environ["MCP_SERVER_URL"] = original_mcp_url or "http://mcp-fixture.invalid"
        def reject_postgres(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("A avaliação não pode conectar ao PostgreSQL")

        main.psycopg.connect = reject_postgres
        main.CatalogMcpClient = lambda _url: catalog
        main.get_purchase_agent = lambda: agent
        with TestClient(main.app) as client:
            response = client.post("/requisicoes", json={"pedido": scenario.pedido})
        payload = response.json()
        if response.status_code != scenario.expected_status:
            return False, f"status esperado {scenario.expected_status}, recebido {response.status_code}"
        if scenario.expected_code:
            code = payload.get("erro", {}).get("codigo")
            if code != scenario.expected_code:
                return False, f"código esperado {scenario.expected_code}, recebido {code}"
        if response.status_code == 201:
            requisition = payload["requisicao"]
            item = requisition["itens"][0]
            product = PRODUCTS[item["produtoId"]]
            if requisition["ferramentasChamadas"] != ["buscar_produtos", "detalhar_produto", "criar_requisicao"]:
                return False, "telemetria não confirma busca, validação e tool de persistência MCP"
            if product.category != "laptops" or product.price > Decimal("1500"):
                return False, "produto não atende categoria ou teto da fixture"
            if item["quantidade"] != scenario.quantity:
                return False, "quantidade retornada diverge da quantidade solicitada"
            expected_total = product.price * scenario.quantity
            if Decimal(str(requisition["valorTotal"])) != expected_total:
                return False, "total retornado não corresponde a preço × quantidade"
        expected_rows = 1 if response.status_code == 201 else 0
        if len(database.requests) != expected_rows or len(database.items) != expected_rows:
            return False, "persistência em memória diverge do resultado esperado"
        expected_writer_calls = 1 if response.status_code == 201 else 0
        if catalog.writer_calls != expected_writer_calls:
            return False, "chamada ao MCP writer diverge do resultado esperado"
        return True, scenario.rule
    finally:
        main.psycopg.connect = original_connect
        main.CatalogMcpClient = original_catalog
        main.get_purchase_agent = original_agent
        if original_mcp_url is None:
            os.environ.pop("MCP_SERVER_URL", None)
        else:
            os.environ["MCP_SERVER_URL"] = original_mcp_url


def main_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Avalia o agente de compras com fixtures determinísticas.")
    parser.add_argument("--live", action="store_true", help="Executa os cinco cenários com o LLM configurado; pode gerar custo.")
    parser.add_argument("--confirm-paid", action="store_true", help="Confirma explicitamente chamadas pagas; obrigatório com --live.")
    parser.add_argument("--max-cost-usd", type=Decimal, help="Teto de custo para --live, limitado a US$ 0,50.")
    args = parser.parse_args(argv)
    if args.live:
        if not args.confirm_paid:
            parser.error("--live exige --confirm-paid")
        if args.max_cost_usd is None:
            parser.error("--live exige --max-cost-usd até 0.50")
        if not args.max_cost_usd.is_finite() or args.max_cost_usd <= 0 or args.max_cost_usd > Decimal("0.50"):
            parser.error("--max-cost-usd deve ser maior que zero e não passar de 0.50")
        from evaluation.live import run_live_evaluation

        return run_live_evaluation(args.max_cost_usd)
    if args.confirm_paid:
        parser.error("--confirm-paid só pode ser usado com --live")
    if args.max_cost_usd is not None:
        parser.error("--max-cost-usd só pode ser usado com --live")
    passed = 0
    for scenario in SCENARIOS:
        ok, reason = run_scenario(scenario)
        status = "PASS" if ok else "FAIL"
        print(f"{status} — {scenario.name}: {reason}")
        passed += int(ok)
    print(f"Resultado: {passed}/{len(SCENARIOS)}")
    return 0 if passed == len(SCENARIOS) else 1


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv[1:]))
