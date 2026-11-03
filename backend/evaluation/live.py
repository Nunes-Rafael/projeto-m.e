from __future__ import annotations

import asyncio
import json
import os
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from app import main
from app.agent import MAX_TOOL_CALLS, AgentError, AgentProviderError
from app.mcp_client import McpClientError

APPROVED_MAX_COST_USD = Decimal("0.50")
MODEL = "gpt-5.4-nano"
INPUT_USD_PER_MILLION_TOKENS = Decimal("0.20")
OUTPUT_USD_PER_MILLION_TOKENS = Decimal("1.25")
APPROVED_PRICE_PROFILE = (Decimal("0.20"), Decimal("1.25"))
COST_SAFETY_MULTIPLIER = Decimal("1.25")
MAX_COMPLETION_TOKENS = 512
MAX_REQUEST_BODY_BYTES = 32 * 1024
INPUT_TOKEN_OVERHEAD = 4_096
MAX_CASES = 5
MAX_PROVIDER_REQUESTS = MAX_CASES * MAX_TOOL_CALLS


class LiveEvaluationError(Exception):
    """A safe-to-display failure in the opt-in evaluation runner."""


@dataclass(frozen=True)
class Product:
    id: int
    title: str
    category: str
    price: Decimal
    aliases: tuple[str, ...]

    def as_catalog_product(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "titulo": self.title,
            "preco": float(self.price),
            "categoria": self.category,
            "marca": "Fixture",
        }


PRODUCTS = {
    1: Product(1, "Notebook para escritório 16 GB", "laptops", Decimal("1250.00"), ("notebook", "notebooks", "laptop", "laptops", "computador")),
    2: Product(2, "Notebook premium 32 GB", "laptops", Decimal("1850.00"), ("notebook", "notebooks", "laptop", "laptops", "computador")),
    3: Product(3, "Monitor 27 polegadas IPS", "monitors", Decimal("320.00"), ("monitor", "monitores", "display")),
    4: Product(4, "Monitor 32 polegadas UHD", "monitors", Decimal("510.00"), ("monitor", "monitores", "display")),
    5: Product(5, "Smartphone 5G 128 GB", "phones", Decimal("699.00"), ("smartphone", "smartphones", "celular", "telefone", "phone")),
    6: Product(6, "Smartphone 4G 128 GB", "phones", Decimal("399.00"), ("smartphone", "smartphones", "celular", "telefone", "phone")),
    7: Product(7, "Mouse ergonômico sem fio", "accessories", Decimal("39.00"), ("mouse", "mouses", "rato")),
    8: Product(8, "Mouse gamer com fio", "accessories", Decimal("65.00"), ("mouse", "mouses", "rato")),
    9: Product(9, "Teclado mecânico compacto", "accessories", Decimal("89.00"), ("teclado", "teclados", "keyboard")),
    10: Product(10, "Teclado básico para escritório", "accessories", Decimal("29.00"), ("teclado", "teclados", "keyboard")),
}


@dataclass(frozen=True)
class Scenario:
    name: str
    pedido: str
    accepted_product_ids: frozenset[int]
    quantity: int
    max_unit_price: Decimal


SCENARIOS = (
    Scenario("notebook com teto", "Preciso de 3 notebooks para a equipe administrativa, até US$ 1.500 cada.", frozenset({1}), 3, Decimal("1500.00")),
    Scenario("monitor de 27 polegadas", "Preciso de 2 monitores de 27 polegadas para o escritório, até US$ 400 por unidade.", frozenset({3}), 2, Decimal("400.00")),
    Scenario("celular com 5G", "Preciso de 1 smartphone com 5G, até US$ 750 cada.", frozenset({5}), 1, Decimal("750.00")),
    Scenario("mouse ergonômico", "Preciso de 4 mouses ergonômicos sem fio, até US$ 50 cada.", frozenset({7}), 4, Decimal("50.00")),
    Scenario("teclado mecânico compacto", "Preciso de 2 teclados mecânicos compactos, até US$ 100 cada.", frozenset({9}), 2, Decimal("100.00")),
)


class FixtureCatalog:
    """Catalog and writer double; neither opens network connections nor SQL."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "buscar_produtos":
            return _tool_result({"produtos": self._search(arguments["termo"])})
        if name == "detalhar_produto":
            product = PRODUCTS.get(arguments["id"])
            if product is None:
                raise McpClientError("Fixture product not found")
            return _tool_result({**product.as_catalog_product(), "descricao": "Produto sintético para avaliação.", "estoque": 20})
        raise McpClientError("Fixture tool not found")

    async def create_requisition(self, payload: dict[str, Any]) -> Any:
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
        total = sum((Decimal(item["valor_total"]) for item in payload["itens"]), Decimal("0.00"))
        requisition = {
            "numero": len(self.requests) + 1,
            "pedido": payload["pedido_original"],
            "itens": items,
            "valorTotal": float(total),
            "criadaEm": "2026-01-01T00:00:00+00:00",
        }
        self.requests.append(requisition)
        self.items.extend(items)
        return _tool_result({"requisicao": requisition})

    @staticmethod
    def _search(term: str) -> list[dict[str, Any]]:
        query = _normalize(term)
        if len(query) < 2 or len(term) > 120:
            raise McpClientError("Invalid fixture search term")
        found = []
        for product in PRODUCTS.values():
            terms = (product.title, product.category, *product.aliases)
            if any(query in _normalize(alias) or _normalize(alias) in query for alias in terms):
                found.append(product.as_catalog_product())
        return found


class CostGuard:
    def __init__(self, max_cost_usd: Decimal) -> None:
        self.max_cost_usd = max_cost_usd
        self.requests = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.pending_request_cost = Decimal("0")

    @property
    def estimated_cost_usd(self) -> Decimal:
        raw_cost = (
            Decimal(self.prompt_tokens) * INPUT_USD_PER_MILLION_TOKENS
            + Decimal(self.completion_tokens) * OUTPUT_USD_PER_MILLION_TOKENS
        ) / Decimal(1_000_000)
        return raw_cost * COST_SAFETY_MULTIPLIER

    def before_request(self, payload: dict[str, Any]) -> None:
        request_bytes = len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii"))
        if request_bytes > MAX_REQUEST_BODY_BYTES:
            raise LiveEvaluationError("request_size_limit")
        if self.requests >= MAX_PROVIDER_REQUESTS:
            raise LiveEvaluationError("provider_request_limit")

        max_prompt_tokens = request_bytes + INPUT_TOKEN_OVERHEAD
        input_cost = Decimal(max_prompt_tokens) * INPUT_USD_PER_MILLION_TOKENS
        output_cost = Decimal(MAX_COMPLETION_TOKENS) * OUTPUT_USD_PER_MILLION_TOKENS
        upper_bound = (input_cost + output_cost) / Decimal(1_000_000) * COST_SAFETY_MULTIPLIER
        if self.estimated_cost_usd + upper_bound > self.max_cost_usd:
            raise LiveEvaluationError("cost_limit_before_request")
        self.pending_request_cost = upper_bound
        self.requests += 1

    def record_usage(self, usage: Any) -> None:
        if not isinstance(usage, dict):
            raise LiveEvaluationError("provider_usage_missing")
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        if type(prompt_tokens) is not int or type(completion_tokens) is not int or min(prompt_tokens, completion_tokens) < 0:
            raise LiveEvaluationError("provider_usage_invalid")

        request_cost = (
            Decimal(prompt_tokens) * INPUT_USD_PER_MILLION_TOKENS
            + Decimal(completion_tokens) * OUTPUT_USD_PER_MILLION_TOKENS
        ) / Decimal(1_000_000) * COST_SAFETY_MULTIPLIER
        if request_cost > self.pending_request_cost:
            raise LiveEvaluationError("provider_usage_exceeded_preflight")
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.pending_request_cost = Decimal("0")
        if self.estimated_cost_usd > self.max_cost_usd:
            raise LiveEvaluationError("cost_limit_after_response")


def run_live_evaluation(max_cost_usd: Decimal) -> int:
    model = os.getenv("OPENAI_MODEL", "").strip()
    if os.getenv("AGENT_MODE", "").strip().lower() != "openai":
        return _configuration_error("AGENT_MODE must be openai")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return _configuration_error("OPENAI_API_KEY is not configured")
    if model != MODEL:
        return _configuration_error("Configured model has no approved price entry")
    if (INPUT_USD_PER_MILLION_TOKENS, OUTPUT_USD_PER_MILLION_TOKENS) != APPROVED_PRICE_PROFILE:
        return _configuration_error("Configured model price profile has changed")
    if max_cost_usd > APPROVED_MAX_COST_USD:
        return _configuration_error("Requested budget exceeds the approved limit")

    guard = CostGuard(max_cost_usd)
    print(
        f"Avaliação real opt-in — modelo={model}; cenários={len(SCENARIOS)}; "
        f"teto=US$ {max_cost_usd:.2f}; máximo de chamadas={MAX_PROVIDER_REQUESTS}; "
        f"saída por chamada={MAX_COMPLETION_TOKENS} tokens; corpo máximo={MAX_REQUEST_BODY_BYTES // 1024} KiB; "
        f"limite máximo calculado=US$ {_max_run_cost():.5f}."
    )
    passed = 0
    for scenario in SCENARIOS:
        start_requests = guard.requests
        start_prompt = guard.prompt_tokens
        start_completion = guard.completion_tokens
        start_cost = guard.estimated_cost_usd
        fixture = FixtureCatalog()
        api = main.get_purchase_agent(
            request_guard=guard,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )
        catalog = main.ExecutionCatalog(fixture, scenario.pedido, main._price_limit(scenario.pedido))

        try:
            decision = asyncio.run(api.decide(scenario.pedido, catalog))
            if guard.pending_request_cost:
                raise LiveEvaluationError("provider_usage_missing")
            success, reason = _score(scenario, decision, catalog, fixture)
        except AgentProviderError:
            print("STOP — provedor indisponível; nenhuma nova chamada será feita.")
            _print_usage(guard)
            return 2
        except AgentError:
            success, reason = False, "o agente não retornou uma decisão válida"
        except LiveEvaluationError as error:
            print(f"STOP — limite de segurança: {error}.")
            _print_usage(guard)
            return 2
        except Exception:
            print(f"STOP — {scenario.name}: falha interna; nenhuma nova chamada será feita.")
            _print_usage(guard)
            return 2

        current_requests = guard.requests - start_requests
        prompt_tokens = guard.prompt_tokens - start_prompt
        completion_tokens = guard.completion_tokens - start_completion
        estimated_cost = guard.estimated_cost_usd - start_cost
        print(
            f"{'PASS' if success else 'FAIL'} — {scenario.name}: {reason}; "
            f"chamadas={current_requests}; tokens={prompt_tokens}+{completion_tokens}; "
            f"estimativa=US$ {estimated_cost:.5f}."
        )
        passed += int(success)

    print(f"Resultado: {passed}/{len(SCENARIOS)}")
    _print_usage(guard)
    return 0 if passed == len(SCENARIOS) else 1


def _score(scenario: Scenario, decision: Any, catalog: Any, fixture: FixtureCatalog) -> tuple[bool, str]:
    requisition = catalog.persisted_requisition
    if requisition is None:
        return False, "nenhuma requisição foi criada no gravador em memória"
    tools = catalog.tools_called
    if not {"buscar_produtos", "detalhar_produto", "criar_requisicao"}.issubset(tools):
        return False, "tools de busca, detalhe e criação não foram confirmadas"
    items = requisition.get("itens", [])
    if len(items) != 1:
        return False, "quantidade de itens diferente do esperado"
    item = items[0]
    if item.get("produtoId") not in scenario.accepted_product_ids:
        return False, "produto escolhido fora do conjunto aceito"
    selected_items = [selected.model_dump() for selected in decision.itens]
    if len(selected_items) != 1 or selected_items[0]["produto_id"] != item.get("produtoId"):
        return False, "decisão do agente diverge do item persistido em memória"
    if item.get("quantidade") != scenario.quantity or selected_items[0]["quantidade"] != scenario.quantity:
        return False, "quantidade divergente do pedido"
    unit_price = Decimal(str(item.get("precoUnitario")))
    if unit_price > scenario.max_unit_price:
        return False, "preço unitário acima do teto"
    expected_total = unit_price * scenario.quantity
    if Decimal(str(item.get("valorTotal"))) != expected_total:
        return False, "total do item diferente de preço × quantidade"
    if Decimal(str(requisition.get("valorTotal"))) != expected_total:
        return False, "total diferente de preço × quantidade"
    if len(fixture.requests) != 1 or len(fixture.items) != 1:
        return False, "persistência em memória não ocorreu uma única vez"
    return True, "produto, quantidade, teto e total válidos"


def _tool_result(payload: dict[str, Any]) -> Any:
    return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload, ensure_ascii=False))])


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _max_run_cost() -> Decimal:
    max_prompt_tokens = MAX_REQUEST_BODY_BYTES + INPUT_TOKEN_OVERHEAD
    raw_input = Decimal(MAX_PROVIDER_REQUESTS * max_prompt_tokens) * INPUT_USD_PER_MILLION_TOKENS
    raw_output = Decimal(MAX_PROVIDER_REQUESTS * MAX_COMPLETION_TOKENS) * OUTPUT_USD_PER_MILLION_TOKENS
    return (raw_input + raw_output) / Decimal(1_000_000) * COST_SAFETY_MULTIPLIER


def _print_usage(guard: CostGuard) -> None:
    pending = guard.pending_request_cost
    print(
        f"Uso agregado: chamadas={guard.requests}; tokens={guard.prompt_tokens}+{guard.completion_tokens}; "
        f"estimativa registrada=US$ {guard.estimated_cost_usd:.5f}; "
        f"reserva da chamada sem usage=US$ {pending:.5f}."
    )


def _configuration_error(code: str) -> int:
    print(f"ERRO — configuração da avaliação: {code}.")
    return 2
