from __future__ import annotations

import os
import secrets
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo


@pytest.fixture
def migrated_runtime_roles(monkeypatch):
    owner_url = os.getenv("MIGRATION_TEST_DATABASE_URL", "").strip()
    if not owner_url:
        pytest.skip("Defina MIGRATION_TEST_DATABASE_URL para um banco exclusivo *_test")
    database_name = conninfo_to_dict(owner_url).get("dbname", "")
    if not database_name.endswith("_test"):
        pytest.fail("MIGRATION_TEST_DATABASE_URL deve usar banco exclusivo com sufixo _test")

    suffix = uuid4().hex[:10]
    api_role = f"api_test_{suffix}"
    mcp_role = f"mcp_test_{suffix}"
    elevated_group = f"elevated_test_{suffix}"
    api_password = secrets.token_hex(32)
    mcp_password = secrets.token_hex(32)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", owner_url)
    monkeypatch.setenv("POSTGRES_DB", "ignored_database_name_test")
    monkeypatch.setenv("PURCHASE_API_DB_USER", api_role)
    monkeypatch.setenv("PURCHASE_API_DB_PASSWORD", api_password)
    monkeypatch.setenv("MCP_DB_USER", mcp_role)
    monkeypatch.setenv("MCP_DB_PASSWORD", mcp_password)

    with psycopg.connect(owner_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(api_role)))
        connection.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(mcp_role)))
        connection.execute(sql.SQL("CREATE ROLE {} CREATEDB").format(sql.Identifier(elevated_group)))
        connection.execute(sql.SQL("GRANT {} TO {}, {}").format(sql.Identifier(elevated_group), sql.Identifier(api_role), sql.Identifier(mcp_role)))

    from app.migrate import migrate

    migrate()
    try:
        writer_url = make_conninfo(owner_url, user=mcp_role, password=mcp_password)
        yield owner_url, api_role, mcp_role, writer_url, elevated_group
    finally:
        with psycopg.connect(owner_url, autocommit=True) as connection:
            for role_name in (api_role, mcp_role):
                role = sql.Identifier(role_name)
                connection.execute(sql.SQL("DROP OWNED BY {}").format(role))
                connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(role))
            connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(elevated_group)))


def test_runtime_roles_have_least_privilege_grants(migrated_runtime_roles) -> None:
    database_url, api_role, mcp_role, _, elevated_group = migrated_runtime_roles
    with psycopg.connect(database_url) as connection:
        for role in (api_role, mcp_role):
            assert connection.execute(
                "SELECT has_schema_privilege(%s, 'public', 'USAGE'), has_schema_privilege(%s, 'public', 'CREATE')",
                (role, role),
            ).fetchone() == (True, False)
            attributes = connection.execute(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolcanlogin, rolinherit, rolbypassrls FROM pg_roles WHERE rolname = %s",
                (role,),
            ).fetchone()
            assert attributes == (False, False, False, True, False, False)
            assert connection.execute("SELECT pg_has_role(%s, %s, 'MEMBER')", (role, elevated_group)).fetchone() == (False,)
            for table in ("requisicoes", "itens_requisicao"):
                assert connection.execute(
                    "SELECT pg_get_userbyid(relowner) = %s FROM pg_class WHERE oid = %s::regclass",
                    (role, table),
                ).fetchone() == (False,)

        for table in ("requisicoes", "itens_requisicao"):
            api_privileges = connection.execute(
                "SELECT has_table_privilege(%s, %s, 'SELECT'), has_table_privilege(%s, %s, 'INSERT'), has_table_privilege(%s, %s, 'UPDATE'), has_table_privilege(%s, %s, 'DELETE')",
                (api_role, table, api_role, table, api_role, table, api_role, table),
            ).fetchone()
            assert api_privileges == (True, False, False, False)

            mcp_privileges = connection.execute(
                "SELECT has_table_privilege(%s, %s, 'SELECT'), has_table_privilege(%s, %s, 'INSERT'), has_table_privilege(%s, %s, 'UPDATE'), has_table_privilege(%s, %s, 'DELETE')",
                (mcp_role, table, mcp_role, table, mcp_role, table, mcp_role, table),
            ).fetchone()
            assert mcp_privileges == (True, True, False, False)

        api_sequence_privileges = connection.execute(
            "SELECT has_sequence_privilege(%s, 'requisicoes_numero_seq', 'USAGE'), has_sequence_privilege(%s, 'requisicoes_numero_seq', 'SELECT'), has_sequence_privilege(%s, 'requisicoes_numero_seq', 'UPDATE')",
            (api_role, api_role, api_role),
        ).fetchone()
        assert api_sequence_privileges == (False, False, False)
        mcp_sequence_privileges = connection.execute(
            "SELECT has_sequence_privilege(%s, 'requisicoes_numero_seq', 'USAGE'), has_sequence_privilege(%s, 'requisicoes_numero_seq', 'SELECT'), has_sequence_privilege(%s, 'requisicoes_numero_seq', 'UPDATE')",
            (mcp_role, mcp_role, mcp_role),
        ).fetchone()
        assert mcp_sequence_privileges == (True, True, False)


def test_runtime_mcp_role_can_create_header_and_items_without_owner_credentials(migrated_runtime_roles) -> None:
    _, _, _, writer_url, _ = migrated_runtime_roles
    key = uuid4()
    with psycopg.connect(writer_url) as connection:
        request_id, number = connection.execute(
            "INSERT INTO requisicoes (chave_idempotencia, hash_payload, pedido_original, valor_total) VALUES (%s, %s, %s, %s) RETURNING id, numero",
            (key, "a" * 64, "1 notebook", "10.00"),
        ).fetchone()
        connection.execute(
            "INSERT INTO itens_requisicao (requisicao_id, produto_origem_id, titulo, quantidade, preco_unitario, valor_total) VALUES (%s, %s, %s, %s, %s, %s)",
            (request_id, 1, "Notebook", 1, "10.00", "10.00"),
        )
        assert connection.execute(
            "SELECT count(*) FROM itens_requisicao WHERE requisicao_id = %s",
            (request_id,),
        ).fetchone() == (1,)
    assert number > 0


def test_database_constraint_rejects_inconsistent_line_and_rolls_back_header(migrated_runtime_roles) -> None:
    database_url, _, _, writer_url, _ = migrated_runtime_roles
    key = uuid4()
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(writer_url) as connection:
            request_id = connection.execute(
                "INSERT INTO requisicoes (chave_idempotencia, hash_payload, pedido_original, valor_total) VALUES (%s, %s, %s, %s) RETURNING id",
                (key, "b" * 64, "pedido inconsistente", "20.00"),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO itens_requisicao (requisicao_id, produto_origem_id, titulo, quantidade, preco_unitario, valor_total) VALUES (%s, %s, %s, %s, %s, %s)",
                (request_id, 2, "Item", 2, "10.00", "19.00"),
            )
    with psycopg.connect(database_url) as connection:
        assert connection.execute("SELECT count(*) FROM requisicoes WHERE chave_idempotencia = %s", (key,)).fetchone() == (0,)


def test_invalid_existing_superuser_leaves_all_runtime_roles_unchanged(monkeypatch) -> None:
    owner_url = os.getenv("MIGRATION_TEST_DATABASE_URL", "").strip()
    if not owner_url:
        pytest.skip("Defina MIGRATION_TEST_DATABASE_URL para um banco exclusivo *_test")
    database_name = conninfo_to_dict(owner_url).get("dbname", "")
    if not database_name.endswith("_test"):
        pytest.fail("MIGRATION_TEST_DATABASE_URL deve usar banco exclusivo com sufixo _test")

    suffix = uuid4().hex[:10]
    api_role = f"api_bad_{suffix}"
    mcp_role = f"mcp_bad_{suffix}"
    api_password = secrets.token_hex(32)
    mcp_password = secrets.token_hex(32)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", owner_url)
    monkeypatch.setenv("POSTGRES_DB", database_name)
    monkeypatch.setenv("PURCHASE_API_DB_USER", api_role)
    monkeypatch.setenv("PURCHASE_API_DB_PASSWORD", api_password)
    monkeypatch.setenv("MCP_DB_USER", mcp_role)
    monkeypatch.setenv("MCP_DB_PASSWORD", mcp_password)

    with psycopg.connect(owner_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE ROLE {} WITH LOGIN CREATEDB PASSWORD {}").format(sql.Identifier(api_role), sql.Literal(api_password))
        )
        connection.execute(
            sql.SQL("CREATE ROLE {} WITH LOGIN SUPERUSER PASSWORD {}").format(sql.Identifier(mcp_role), sql.Literal(mcp_password))
        )
        before = connection.execute(
            "SELECT rolname, rolsuper, rolcreatedb, rolpassword FROM pg_authid WHERE rolname IN (%s, %s) ORDER BY rolname",
            (api_role, mcp_role),
        ).fetchall()

    from app.migrate import migrate

    try:
        with pytest.raises(RuntimeError, match="administrativos"):
            migrate()
        with psycopg.connect(owner_url) as connection:
            after = connection.execute(
                "SELECT rolname, rolsuper, rolcreatedb, rolpassword FROM pg_authid WHERE rolname IN (%s, %s) ORDER BY rolname",
                (api_role, mcp_role),
            ).fetchall()
        assert after == before
    finally:
        with psycopg.connect(owner_url, autocommit=True) as connection:
            for role_name in (api_role, mcp_role):
                role = sql.Identifier(role_name)
                connection.execute(sql.SQL("DROP OWNED BY {}").format(role))
                connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(role))


@pytest.mark.parametrize(
    ("api_user", "mcp_user", "owner_user"),
    [
        ("same_role", "same_role", "owner"),
        ("owner", "mcp", "owner"),
        ("api", "owner", "owner"),
    ],
)
def test_runtime_role_names_must_be_distinct(api_user, mcp_user, owner_user):
    from app.migrate import validate_runtime_role_names

    with pytest.raises(ValueError, match="distintos"):
        validate_runtime_role_names(api_user, mcp_user, owner_user)
