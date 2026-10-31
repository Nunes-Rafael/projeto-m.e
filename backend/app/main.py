import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI


SCHEMA = """
CREATE TABLE IF NOT EXISTS requisicoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero BIGSERIAL UNIQUE NOT NULL,
    pedido_original TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'criada' CHECK (status = 'criada'),
    valor_total NUMERIC(12, 2) NOT NULL CHECK (valor_total >= 0),
    criada_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS itens_requisicao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requisicao_id UUID NOT NULL REFERENCES requisicoes(id) ON DELETE CASCADE,
    produto_origem_id INTEGER NOT NULL CHECK (produto_origem_id > 0),
    titulo TEXT NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(12, 2) NOT NULL CHECK (preco_unitario >= 0),
    valor_total NUMERIC(12, 2) NOT NULL CHECK (valor_total >= 0)
);

CREATE INDEX IF NOT EXISTS itens_requisicao_requisicao_id_idx
    ON itens_requisicao (requisicao_id);
CREATE INDEX IF NOT EXISTS requisicoes_criada_em_idx
    ON requisicoes (criada_em DESC);
"""


def initialize_database() -> None:
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            cursor.execute(SCHEMA)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield

app = FastAPI(title="Purchase Agent API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
