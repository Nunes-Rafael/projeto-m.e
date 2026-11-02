from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from typing import Any, Protocol

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import BaseModel, Field, ValidationError, field_validator

ALLOWED_TOOLS = frozenset({"buscar_produtos", "detalhar_produto"})
PERSISTENCE_TOOL = "criar_requisicao"


class McpClientError(Exception):
    """Stable backend error for MCP transport and protocol failures."""


class SearchProductsArguments(BaseModel):
    termo: str = Field(min_length=2, max_length=120)

    @field_validator("termo")
    @classmethod
    def normalize_term(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("termo deve ter entre 2 e 120 caracteres")
        return normalized


class ProductDetailsArguments(BaseModel):
    id: int = Field(gt=0)


class McpSession(Protocol):
    async def initialize(self) -> Any: ...
    async def list_tools(self) -> Any: ...
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class CatalogMcpClient:
    def __init__(self, server_url: str) -> None:
        self.server_url = server_url.rstrip("/") + "/mcp"
        self.service_token = os.getenv("MCP_WRITE_TOKEN", "").strip()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in ALLOWED_TOOLS:
            raise McpClientError("Ferramenta MCP não permitida")
        validated_arguments = self._validate_arguments(name, arguments)
        return await self._call(name, validated_arguments, ALLOWED_TOOLS)

    async def create_requisition(self, payload: dict[str, Any]) -> Any:
        if not self.service_token:
            raise McpClientError("Autenticação de serviço indisponível")
        return await self._call(PERSISTENCE_TOOL, payload, frozenset({PERSISTENCE_TOOL}))

    async def _call(self, name: str, arguments: dict[str, Any], required_tools: frozenset[str]) -> Any:
        if not self.service_token:
            raise McpClientError("Autenticação de serviço indisponível")
        try:
            async with self._session() as session:
                await session.initialize()
                tools = await session.list_tools()
                available_tools = {tool.name for tool in tools.tools}
                if not required_tools.issubset(available_tools):
                    raise McpClientError("Ferramentas MCP indisponíveis")
                result = await session.call_tool(name, arguments=arguments)
        except McpClientError:
            raise
        except Exception as error:
            raise McpClientError("Não foi possível consultar o catálogo agora") from error
        if getattr(result, "isError", False):
            raise McpClientError("Não foi possível consultar o catálogo agora")
        return result

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[McpSession]:
        async with streamablehttp_client(
            self.server_url,
            headers={"Authorization": f"Bearer {self.service_token}"},
        ) as streams:
            read_stream, write_stream, _ = streams
            async with ClientSession(read_stream, write_stream) as session:
                yield session

    @staticmethod
    def _validate_arguments(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        model = SearchProductsArguments if name == "buscar_produtos" else ProductDetailsArguments
        try:
            return model.model_validate(arguments).model_dump()
        except ValidationError as error:
            raise McpClientError("Argumentos inválidos para ferramenta MCP") from error
