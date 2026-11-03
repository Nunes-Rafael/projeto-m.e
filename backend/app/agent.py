from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.mcp_client import CatalogMcpClient, McpClientError

MAX_TOOL_CALLS = 6
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class AgentError(Exception):
    pass


class AgentConfigurationError(AgentError):
    pass


class AgentProviderError(AgentError):
    def __init__(self, reason: str) -> None:
        self.reason = reason


class AgentPersistenceError(AgentError):
    pass


class NoCompatibleProductError(AgentError):
    pass


class SelectedItem(BaseModel):
    produto_id: int = Field(gt=0, strict=True)
    quantidade: int = Field(ge=1, le=100, strict=True)


class AgentDecision(BaseModel):
    itens: list[SelectedItem] = Field(min_length=1)
    justificativa: str = Field(min_length=1, max_length=1_000)


class PurchaseAgent(Protocol):
    async def decide(self, pedido: str, catalog: CatalogMcpClient) -> AgentDecision: ...


class ProviderRequestGuard(Protocol):
    def before_request(self, payload: dict[str, Any]) -> None: ...
    def record_usage(self, usage: Any) -> None: ...


def get_purchase_agent(
    request_guard: ProviderRequestGuard | None = None,
    max_completion_tokens: int | None = None,
) -> PurchaseAgent:
    mode = os.getenv("AGENT_MODE", "local").lower()
    if mode == "local":
        return LocalPurchaseAgent()
    if mode == "openrouter":
        return OpenRouterPurchaseAgent.from_environment(
            request_guard=request_guard,
            max_completion_tokens=max_completion_tokens,
        )
    if mode == "openai":
        return OpenRouterPurchaseAgent.from_environment(
            api_key_name="OPENAI_API_KEY",
            model_name="OPENAI_MODEL",
            api_url=OPENAI_URL,
            request_guard=request_guard,
            max_completion_tokens=max_completion_tokens,
        )
    raise AgentConfigurationError("Modo de agente inválido")


class LocalPurchaseAgent:
    async def decide(self, pedido: str, catalog: CatalogMcpClient) -> AgentDecision:
        quantity = _extract_quantity(pedido)
        term = _extract_term(pedido)
        products = _read_tool_result(await catalog.call_tool("buscar_produtos", {"termo": term}))
        candidates = products.get("produtos", [])
        if not candidates:
            raise NoCompatibleProductError("Nenhum produto compatível foi encontrado")
        product = candidates[0]
        arguments = {
            "itens": [{"produto_id": product["id"], "quantidade": quantity}],
            "justificativa": "Modo local: seleção determinística para desenvolvimento.",
        }
        _read_tool_result(await catalog.call_tool("criar_requisicao", arguments))
        return AgentDecision(
            itens=[SelectedItem(produto_id=product["id"], quantidade=quantity)],
            justificativa="Modo local: seleção determinística para desenvolvimento.",
        )


class OpenRouterPurchaseAgent:
    def __init__(
        self,
        api_key: str,
        model: str,
        api_url: str = OPENROUTER_URL,
        request_guard: ProviderRequestGuard | None = None,
        max_completion_tokens: int | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.request_guard = request_guard
        self.max_completion_tokens = max_completion_tokens

    @classmethod
    def from_environment(
        cls,
        api_key_name: str = "OPENROUTER_API_KEY",
        model_name: str = "OPENROUTER_MODEL",
        api_url: str = OPENROUTER_URL,
        request_guard: ProviderRequestGuard | None = None,
        max_completion_tokens: int | None = None,
    ) -> "OpenRouterPurchaseAgent":
        api_key = os.getenv(api_key_name, "").strip()
        model = os.getenv(model_name, "").strip()
        if not api_key or not model:
            raise AgentConfigurationError(f"O modo configurado exige {api_key_name} e {model_name}")
        return cls(api_key, model, api_url, request_guard, max_completion_tokens)

    async def decide(self, pedido: str, catalog: CatalogMcpClient) -> AgentDecision:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "Você é um agente de compras. Use buscar_produtos para consultar o catálogo e nunca invente produtos ou preços. "
                    "Depois de escolher produtos compatíveis, chame criar_requisicao informando somente produto_id e quantidade; "
                    "a tool só aparecerá após existir resultado de busca. Não envie preço nem total."
                ),
            },
            {"role": "user", "content": pedido},
        ]
        tool_calls_made = 0
        async with httpx.AsyncClient(timeout=15) as client:
            for _ in range(MAX_TOOL_CALLS):
                try:
                    request_payload = {
                        "model": self.model,
                        "messages": messages,
                        "tools": _tool_schemas(bool(getattr(catalog, "searched_product_ids", set()))),
                    }
                    if self.max_completion_tokens is not None:
                        request_payload["max_completion_tokens"] = self.max_completion_tokens
                    if self.request_guard is not None:
                        self.request_guard.before_request(request_payload)
                    response = await client.post(
                        self.api_url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=request_payload,
                    )
                    response.raise_for_status()
                    provider_response = response.json()
                    if self.request_guard is not None:
                        self.request_guard.record_usage(provider_response.get("usage"))
                    message = provider_response["choices"][0]["message"]
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
                    reason = "provider_unavailable"
                    if isinstance(error, httpx.HTTPStatusError):
                        provider_message = error.response.text.lower()
                        if "limit exceeded" in provider_message or "quota" in provider_message:
                            reason = "key_limit_exceeded"
                    raise AgentProviderError(reason) from error
                messages.append(message)
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    return _parse_decision(message.get("content", ""))
                for call in tool_calls:
                    tool_calls_made += 1
                    if tool_calls_made > MAX_TOOL_CALLS:
                        raise AgentError("O agente excedeu o limite de chamadas de ferramenta")
                    try:
                        name = call["function"]["name"]
                        arguments = json.loads(call["function"]["arguments"])
                    except (KeyError, TypeError, json.JSONDecodeError) as error:
                        raise AgentError("O agente solicitou uma ferramenta inválida") from error
                    if name == "criar_requisicao":
                        if not getattr(catalog, "searched_product_ids", set()):
                            raise AgentError("O agente solicitou gravação sem candidatos do catálogo")
                        try:
                            result = await catalog.call_tool(name, arguments)
                            _read_tool_result(result)
                            return _decision_from_requisition_intent(arguments)
                        except (McpClientError, ValueError, ValidationError) as error:
                            raise AgentPersistenceError("A gravação da requisição não foi confirmada") from error
                    result = await catalog.call_tool(name, arguments)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": json.dumps(_read_tool_result(result)),
                        }
                    )
        raise AgentError("O agente excedeu o limite de chamadas de ferramenta")


def _tool_schemas(include_create: bool = False) -> list[dict[str, Any]]:
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "buscar_produtos",
                "description": "Busca produtos por termo no catálogo.",
                "parameters": {"type": "object", "properties": {"termo": {"type": "string"}}, "required": ["termo"]},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "detalhar_produto",
                "description": "Obtém detalhes de um produto pelo identificador.",
                "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
            },
        },
    ]
    if include_create:
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": "criar_requisicao",
                    "description": "Confirma a intenção de criar a requisição. Informe somente produto_id e quantidade escolhidos no catálogo; o backend valida preços e persiste com segurança.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "itens": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 20,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "produto_id": {"type": "integer", "minimum": 1},
                                        "quantidade": {"type": "integer", "minimum": 1, "maximum": 100},
                                    },
                                    "required": ["produto_id", "quantidade"],
                                    "additionalProperties": False,
                                },
                            },
                            "justificativa": {"type": "string", "maxLength": 1000},
                        },
                        "required": ["itens"],
                        "additionalProperties": False,
                    },
                },
            }
        )
    return schemas


def _decision_from_requisition_intent(arguments: dict[str, Any]) -> AgentDecision:
    try:
        items = [SelectedItem.model_validate(item) for item in arguments["itens"]]
        justification = arguments.get("justificativa") or "Requisição validada e registrada."
        return AgentDecision(itens=items, justificativa=justification)
    except (KeyError, TypeError, ValidationError) as error:
        raise AgentError("A intenção de gravação do agente é inválida") from error


def _read_tool_result(result: Any) -> dict[str, Any]:
    content = getattr(result, "content", [])
    if not content or not getattr(content[0], "text", None):
        raise AgentError("O catálogo retornou dados inválidos")
    try:
        return json.loads(content[0].text)
    except json.JSONDecodeError as error:
        raise AgentError("O catálogo retornou dados inválidos") from error


def _parse_decision(content: str) -> AgentDecision:
    try:
        return AgentDecision.model_validate_json(content)
    except ValidationError as error:
        raise AgentError("O agente retornou uma decisão inválida") from error


def _extract_quantity(pedido: str) -> int:
    match = re.search(r"\b(\d+)\b", pedido)
    return int(match.group(1)) if match else 1


def _extract_term(pedido: str) -> str:
    normalized = pedido.lower()
    for term in ("laptop", "notebook", "phone", "smartphone", "monitor"):
        if term in normalized:
            return "laptop" if term == "notebook" else term
    words = re.findall(r"[a-zA-ZÀ-ÿ]{2,}", normalized)
    return words[-1] if words else "produto"
