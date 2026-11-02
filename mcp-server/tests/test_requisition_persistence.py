from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import logging
import os
import threading
import time
from unittest.mock import Mock
from uuid import uuid4

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import uvicorn

from app import main
from app.main import app, authenticate_service, normalize_requisition, persist_requisition


def sample_payload(key: str | None = None) -> dict:
    return {
        "chave_idempotencia": key or str(uuid4()),
        "pedido_original": "2 notebooks com teto unitário de US$ 2000",
        "itens": [
            {
                "produto_origem_id": 78,
                "titulo": "Notebook de teste",
                "quantidade": 2,
                "preco_unitario": "1999.99",
                "valor_total": "3999.98",
            }
        ],
        "valor_total": "3999.98",
    }


def test_service_authentication_fails_closed() -> None:
    assert authenticate_service("", "Bearer any") == "unavailable"
    assert authenticate_service("expected", "") == "unauthorized"
    assert authenticate_service("expected", "Bearer wrong") == "unauthorized"
    assert authenticate_service("expected", "Bearer expected") == "authorized"


def test_http_auth_denial_happens_before_database_connect(
    isolated_database, mcp_http_server, monkeypatch, caplog
) -> None:
    database_url, schema = isolated_database
    database_connect = Mock(side_effect=AssertionError("database must not be reached"))
    header_sentinel = "auth-header-sentinel-97f2"
    for configured, header, expected_status in (
        (None, None, 503),
        ("expected-token", f"Bearer {header_sentinel}", 401),
    ):
        if configured is None:
            monkeypatch.delenv("MCP_WRITE_TOKEN", raising=False)
            headers = {}
        else:
            monkeypatch.setenv("MCP_WRITE_TOKEN", configured)
            headers = {"Authorization": header}
        with monkeypatch.context() as patcher:
            patcher.setattr(main.psycopg, "connect", database_connect)
            with caplog.at_level(logging.DEBUG):
                response = httpx.post(
                    mcp_http_server,
                    headers=headers,
                    json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                )
        assert response.status_code == expected_status
        assert header_sentinel not in response.text
        assert header_sentinel not in caplog.text
    database_connect.assert_not_called()
    assert read_state(database_url, schema) == (0, 0)


def test_normalized_payload_hash_is_stable_across_item_order() -> None:
    payload = sample_payload()
    second = sample_payload(payload["chave_idempotencia"])
    second["itens"].append(
        {
            "produto_origem_id": 20,
            "titulo": "Mouse de teste",
            "quantidade": 1,
            "preco_unitario": "10.00",
            "valor_total": "10.00",
        }
    )
    payload["itens"].append(second["itens"][1])
    payload["valor_total"] = second["valor_total"] = "4009.98"
    _, first_hash = normalize_requisition(payload)
    second["itens"].reverse()
    _, second_hash = normalize_requisition(second)
    assert first_hash == second_hash


@pytest.mark.parametrize(
    "change",
    [
        lambda payload: payload.update(valor_total="1.00"),
        lambda payload: payload["itens"][0].update(quantidade=101),
        lambda payload: payload["itens"][0].update(preco_unitario="1.0"),
        lambda payload: payload["itens"].append(payload["itens"][0].copy()),
        lambda payload: payload.update(sql="DELETE FROM requisicoes"),
    ],
)
def test_invalid_canonical_payload_is_rejected(change) -> None:
    payload = sample_payload()
    change(payload)
    with pytest.raises(ValueError):
        normalize_requisition(payload)


@pytest.fixture
def isolated_database(monkeypatch):
    database_url = os.getenv("MCP_TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("Defina MCP_TEST_DATABASE_URL apontando para um banco exclusivo *_test")
    parsed = conninfo_to_dict(database_url)
    if not parsed.get("dbname", "").endswith("_test"):
        pytest.fail("MCP_TEST_DATABASE_URL deve usar um banco exclusivo com sufixo _test")

    schema = f"mcp_test_{uuid4().hex}"
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        connection.execute(
            sql.SQL(
                """
                CREATE TABLE {}.requisicoes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    numero BIGSERIAL UNIQUE NOT NULL,
                    chave_idempotencia UUID UNIQUE,
                    hash_payload TEXT,
                    pedido_original TEXT NOT NULL,
                    valor_total NUMERIC(12,2) NOT NULL,
                    criada_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE {}.itens_requisicao (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    requisicao_id UUID NOT NULL REFERENCES {}.requisicoes(id),
                    produto_origem_id INTEGER NOT NULL,
                    titulo TEXT NOT NULL,
                    quantidade INTEGER NOT NULL,
                    preco_unitario NUMERIC(12,2) NOT NULL,
                    valor_total NUMERIC(12,2) NOT NULL,
                    CHECK (valor_total = quantidade * preco_unitario)
                );
                """
            ).format(
                sql.Identifier(schema),
                sql.Identifier(schema),
                sql.Identifier(schema),
            )
        )
        connection.execute(
            sql.SQL(
                """
                CREATE FUNCTION {}.reject_product_999() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.produto_origem_id = 999 THEN RAISE EXCEPTION 'forced item failure'; END IF;
                    RETURN NEW;
                END $$;
                CREATE TRIGGER reject_product_999 BEFORE INSERT ON {}.itens_requisicao
                FOR EACH ROW EXECUTE FUNCTION {}.reject_product_999();
                """
            ).format(
                sql.Identifier(schema),
                sql.Identifier(schema),
                sql.Identifier(schema),
            )
        )
    isolated_url = make_conninfo(database_url, options=f"-csearch_path={schema}")
    monkeypatch.setenv("MCP_DATABASE_URL", isolated_url)
    try:
        yield database_url, schema
    finally:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def read_state(database_url: str, schema: str) -> tuple[int, int]:
    with psycopg.connect(database_url) as connection:
        requisitions, items = connection.execute(
            sql.SQL(
                "SELECT (SELECT count(*) FROM {}.requisicoes), (SELECT count(*) FROM {}.itens_requisicao)"
        ).format(sql.Identifier(schema), sql.Identifier(schema))
        ).fetchone()
    return requisitions, items


@contextmanager
def running_mcp_server():
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=0, log_config=None, access_log=False)
    )
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    for _ in range(200):
        if server.started and server.servers:
            port = server.servers[0].sockets[0].getsockname()[1]
            break
        if not thread.is_alive():
            raise RuntimeError("MCP HTTP server did not start")
        time.sleep(0.01)
    else:
        server.should_exit = True
        thread.join(timeout=2)
        raise RuntimeError("MCP HTTP server startup timed out")
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        thread.join(timeout=3)


@pytest.fixture(scope="module")
def mcp_http_server():
    with running_mcp_server() as server_url:
        yield server_url


async def call_create_tool(server_url: str, token: str, payload: dict) -> dict:
    async with streamablehttp_client(server_url, headers={"Authorization": f"Bearer {token}"}) as streams:
        read_stream, write_stream, _ = streams
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("criar_requisicao", arguments=payload)
    return json.loads(result.content[0].text)


def test_authenticated_http_request_reaches_writer_and_persists(isolated_database, mcp_http_server, monkeypatch) -> None:
    database_url, schema = isolated_database
    token = "test-service-token"
    monkeypatch.setenv("MCP_WRITE_TOKEN", token)
    result = asyncio.run(call_create_tool(mcp_http_server, token, sample_payload()))
    assert result["requisicao"]["numero"] == 1
    assert read_state(database_url, schema) == (1, 1)


def test_authenticated_persistence_error_is_sanitized_in_response_and_logs(
    isolated_database, mcp_http_server, monkeypatch, caplog
) -> None:
    database_url, schema = isolated_database
    token = "auth-header-sentinel-97f2"
    secret_error = "database-password-MUST-NOT-LEAK"
    prompt_sentinel = "prompt-content-sentinel-2ba1"
    product_sentinel = "product-name-sentinel-18ef"
    financial_sentinel = "987654321.09"
    payload = sample_payload()
    payload["pedido_original"] = prompt_sentinel
    payload["itens"][0].update(
        {
            "titulo": product_sentinel,
            "quantidade": 1,
            "preco_unitario": financial_sentinel,
            "valor_total": financial_sentinel,
        }
    )
    payload["valor_total"] = financial_sentinel
    monkeypatch.setenv("MCP_WRITE_TOKEN", token)
    database_connect = Mock(side_effect=RuntimeError(secret_error))
    with monkeypatch.context() as patcher:
        patcher.setattr(main.psycopg, "connect", database_connect)
        with caplog.at_level(logging.INFO):
            result = asyncio.run(call_create_tool(mcp_http_server, token, payload))
    assert result == {"erro": {"codigo": "persistence_unavailable", "mensagem": "Persistência indisponível."}}
    exposed_output = json.dumps(result) + caplog.text
    for sentinel in (secret_error, token, prompt_sentinel, product_sentinel, financial_sentinel):
        assert sentinel not in exposed_output
    assert read_state(database_url, schema) == (0, 0)


def test_same_key_retries_are_idempotent(isolated_database) -> None:
    database_url, schema = isolated_database
    payload = sample_payload()
    first = persist_requisition(payload)
    retry = persist_requisition(payload)
    assert retry == first
    assert read_state(database_url, schema) == (1, 1)


def test_concurrent_same_key_creates_one_request(isolated_database) -> None:
    database_url, schema = isolated_database
    payload = sample_payload()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(persist_requisition, (payload, payload)))
    assert results[0] == results[1]
    assert read_state(database_url, schema) == (1, 1)


def test_reused_key_with_different_payload_conflicts(isolated_database) -> None:
    database_url, schema = isolated_database
    payload = sample_payload()
    persist_requisition(payload)
    changed = sample_payload(payload["chave_idempotencia"])
    changed["itens"][0]["quantidade"] = 1
    changed["itens"][0]["valor_total"] = "1999.99"
    changed["valor_total"] = "1999.99"
    result = persist_requisition(changed)
    assert result["erro"]["codigo"] == "idempotency_conflict"
    assert read_state(database_url, schema) == (1, 1)


def test_item_failure_rolls_back_request_header(isolated_database) -> None:
    database_url, schema = isolated_database
    payload = sample_payload()
    payload["itens"][0]["produto_origem_id"] = 999
    with pytest.raises(psycopg.Error):
        persist_requisition(payload)
    assert read_state(database_url, schema) == (0, 0)
