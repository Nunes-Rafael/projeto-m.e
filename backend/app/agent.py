from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.mcp_client import CatalogMcpClient

MAX_TOOL_CALLS = 6
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class AgentError(Exception):
    pass


class AgentConfigurationError(AgentError):
    pass


class SelectedItem(BaseModel):
    produto_id: int = Field(gt=0)
    quantidade: int = Field(gt=0)


class AgentDecision(BaseModel):
    itens: list[SelectedItem] = Field(min_length=1)
    justificativa: str = Field(min_length=1, max_length=1_000)


class PurchaseAgent(Protocol):
    async def decide(self, pedido: str, catalog: CatalogMcpClient) -> AgentDecision: ...


def get_purchase_agent() -> PurchaseAgent:
    mode = os.getenv("AGENT_MODE", "local").lower()
    if mode == "local":
        return LocalPurchaseAgent()
    if mode == "openrouter":
        return OpenRouterPurchaseAgent.from_environment()
    raise AgentConfigurationError("Modo de agente inválido")


class LocalPurchaseAgent:
    async def decide(self, pedido: str, catalog: CatalogMcpClient) -> AgentDecision:
        quantity = _extract_quantity(pedido)
        term = _extract_term(pedido)
        products = _read_tool_result(await catalog.call_tool("buscar_produtos", {"termo": term}))
        candidates = products.get("produtos", [])
        if not candidates:
            raise AgentError("Nenhum produto compatível foi encontrado")
        product = candidates[0]
        return AgentDecision(
            itens=[SelectedItem(produto_id=product["id"], quantidade=quantity)],
            justificativa="Modo local: seleção determinística para desenvolvimento.",
        )


class OpenRouterPurchaseAgent:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_environment(cls) -> "OpenRouterPurchaseAgent":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model = os.getenv("OPENROUTER_MODEL", "").strip()
        if not api_key or not model:
            raise AgentConfigurationError("O modo OpenRouter exige chave e modelo configurados")
        return cls(api_key, model)

    async def decide(self, pedido: str, catalog: CatalogMcpClient) -> AgentDecision:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "Você é um agente de compras. Use ferramentas quando precisar de dados do catálogo. "
                    "Nunca invente produtos ou preços. Ao finalizar, responda somente JSON com itens "
                    "({produto_id, quantidade}) e justificativa."
                ),
            },
            {"role": "user", "content": pedido},
        ]
        async with httpx.AsyncClient(timeout=15) as client:
            for _ in range(MAX_TOOL_CALLS):
                response = await client.post(
                    OPENROUTER_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": messages, "tools": _tool_schemas()},
                )
                response.raise_for_status()
                message = response.json()["choices"][0]["message"]
                messages.append(message)
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    return _parse_decision(message.get("content", ""))
                for call in tool_calls:
                    name = call["function"]["name"]
                    arguments = json.loads(call["function"]["arguments"])
                    result = await catalog.call_tool(name, arguments)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": json.dumps(_read_tool_result(result)),
                        }
                    )
        raise AgentError("O agente excedeu o limite de chamadas de ferramenta")


def _tool_schemas() -> list[dict[str, Any]]:
    return [
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
            return term
    words = re.findall(r"[a-zA-ZÀ-ÿ]{2,}", normalized)
    return words[-1] if words else "produto"
