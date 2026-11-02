from __future__ import annotations

import os
import re
from dataclasses import dataclass

import psycopg
from psycopg import sql


SCHEMA = """
CREATE TABLE IF NOT EXISTS requisicoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero BIGSERIAL UNIQUE NOT NULL,
    pedido_original TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'criada' CHECK (status = 'criada'),
    valor_total NUMERIC(12, 2) NOT NULL CHECK (valor_total >= 0),
    criada_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE requisicoes ADD COLUMN IF NOT EXISTS chave_idempotencia UUID;
ALTER TABLE requisicoes ADD COLUMN IF NOT EXISTS hash_payload TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS requisicoes_chave_idempotencia_uidx
    ON requisicoes (chave_idempotencia);

DO $$ BEGIN
    ALTER TABLE requisicoes ADD CONSTRAINT requisicoes_idempotencia_pair_check
        CHECK ((chave_idempotencia IS NULL AND hash_payload IS NULL)
            OR (chave_idempotencia IS NOT NULL AND hash_payload IS NOT NULL));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS itens_requisicao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requisicao_id UUID NOT NULL REFERENCES requisicoes(id) ON DELETE CASCADE,
    produto_origem_id INTEGER NOT NULL CHECK (produto_origem_id > 0),
    titulo TEXT NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(12, 2) NOT NULL CHECK (preco_unitario >= 0),
    valor_total NUMERIC(12, 2) NOT NULL CHECK (valor_total >= 0)
);

DO $$ BEGIN
    ALTER TABLE itens_requisicao ADD CONSTRAINT itens_requisicao_total_consistente_check
        CHECK (valor_total = quantidade * preco_unitario) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS itens_requisicao_requisicao_id_idx
    ON itens_requisicao (requisicao_id);
CREATE INDEX IF NOT EXISTS requisicoes_criada_em_idx
    ON requisicoes (criada_em DESC);
"""


def _role_identifier(name: str) -> sql.Identifier:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", name):
        raise ValueError("Nome de role inválido")
    return sql.Identifier(name)


@dataclass(frozen=True)
class RuntimeRolePlan:
    name: str
    exists: bool
    memberships: tuple[str, ...]


def _preflight_runtime_role(cursor, name: str) -> RuntimeRolePlan:
    role = _role_identifier(name)
    cursor.execute(
        "SELECT oid, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname = %s",
        (name,),
    )
    existing = cursor.fetchone()
    if not existing:
        return RuntimeRolePlan(name=name, exists=False, memberships=())
    role_oid, is_superuser, can_create_database, can_create_roles, can_replicate, bypass_rls = existing
    if is_superuser or can_create_database or can_create_roles or can_replicate or bypass_rls:
        raise RuntimeError("Role runtime existente possui privilégios administrativos; configure um role dedicado")
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_class WHERE relowner = %s
            UNION ALL
            SELECT 1 FROM pg_namespace WHERE nspowner = %s
            UNION ALL
            SELECT 1 FROM pg_database WHERE datdba = %s
                AND datname = current_database()
        )
        """,
        (role_oid, role_oid, role_oid),
    )
    if cursor.fetchone()[0]:
        raise RuntimeError("Role de runtime possui objetos ou database; configure um role dedicado")
    cursor.execute(
        """
        SELECT granted.rolname
        FROM pg_auth_members membership
        JOIN pg_roles granted ON granted.oid = membership.roleid
        JOIN pg_roles member ON member.oid = membership.member
        WHERE member.rolname = %s
        """,
        (name,),
    )
    memberships = tuple(granted_role for (granted_role,) in cursor.fetchall())
    return RuntimeRolePlan(name=name, exists=True, memberships=memberships)


def _ensure_role(cursor, plan: RuntimeRolePlan, password: str) -> None:
    role = _role_identifier(plan.name)
    options = sql.SQL("LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT NOBYPASSRLS")
    if plan.exists:
        cursor.execute(sql.SQL("ALTER ROLE {} WITH {} PASSWORD {}").format(role, options, sql.Literal(password)))
    else:
        cursor.execute(sql.SQL("CREATE ROLE {} WITH {} PASSWORD {}").format(role, options, sql.Literal(password)))
    for granted_role in plan.memberships:
        cursor.execute(sql.SQL("REVOKE {} FROM {}").format(sql.Identifier(granted_role), role))


def validate_runtime_role_names(api_user: str, mcp_user: str, owner_user: str) -> None:
    names = (api_user.casefold(), mcp_user.casefold(), owner_user.casefold())
    if len(set(names)) != len(names):
        raise ValueError("Roles de API, MCP e migração devem ser distintos")


def migrate() -> None:
    owner_url = os.getenv("MIGRATION_DATABASE_URL", "").strip()
    api_user = os.getenv("PURCHASE_API_DB_USER", "purchase_api")
    api_password = os.getenv("PURCHASE_API_DB_PASSWORD", "").strip()
    mcp_user = os.getenv("MCP_DB_USER", "purchase_mcp")
    mcp_password = os.getenv("MCP_DB_PASSWORD", "").strip()
    if not owner_url or not api_password or not mcp_password:
        raise RuntimeError("Credenciais de migração ou runtime ausentes")

    with psycopg.connect(owner_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user, current_database()")
            owner_user, database_name = cursor.fetchone()
            validate_runtime_role_names(api_user, mcp_user, owner_user)
            api_plan = _preflight_runtime_role(cursor, api_user)
            mcp_plan = _preflight_runtime_role(cursor, mcp_user)
            cursor.execute(SCHEMA)
            _ensure_role(cursor, api_plan, api_password)
            _ensure_role(cursor, mcp_plan, mcp_password)

            for role_name in (api_user, mcp_user):
                role = _role_identifier(role_name)
                cursor.execute(sql.SQL("REVOKE ALL ON SCHEMA public FROM {}").format(role))
                cursor.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(role))
                cursor.execute(sql.SQL("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {}").format(role))
                cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database_name), role))
                cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))

            api = _role_identifier(api_user)
            cursor.execute(sql.SQL("GRANT SELECT ON requisicoes, itens_requisicao TO {}").format(api))

            mcp = _role_identifier(mcp_user)
            cursor.execute(sql.SQL("GRANT SELECT, INSERT ON requisicoes, itens_requisicao TO {}").format(mcp))
            cursor.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE requisicoes_numero_seq TO {}").format(mcp))


if __name__ == "__main__":
    migrate()
