import asyncio
import json
from types import SimpleNamespace

import pytest

from app.agent import LocalPurchaseAgent


class FakeCatalog:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        if name == "buscar_produtos":
            payload = {"produtos": [{"id": 78}]}
        else:
            payload = {"requisicao": {"numero": 1}}
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])


@pytest.mark.parametrize("pedido", ["preciso de 1 notebook", "preciso de 2 notebooks"])
def test_local_agent_searches_laptop_catalog_for_notebook_requests(pedido: str) -> None:
    catalog = FakeCatalog()

    decision = asyncio.run(LocalPurchaseAgent().decide(pedido, catalog))

    assert catalog.calls[0] == ("buscar_produtos", {"termo": "laptop"})
    assert catalog.calls[1][0] == "criar_requisicao"
    assert decision.itens[0].produto_id == 78
