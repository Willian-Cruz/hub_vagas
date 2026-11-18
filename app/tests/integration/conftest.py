"""
conftest.py — configuração para testes de integração com PostgreSQL.

Configura:
- DATABASE_URL apontando para o banco de teste (PostgreSQL via services: postgres no CI)
- Aplicação automática de migrations antes dos testes
- Limpeza das tabelas entre testes para isolamento

Execução local:
    DATABASE_URL=postgresql+psycopg://hub_vagas:hub_vagas@localhost:5432/hub_vagas \
    pytest app/tests/integration/ -m integration -v
"""
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

# Adiciona raiz do projeto ao path para imports de infra/
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://hub_vagas:hub_vagas@localhost:5432/hub_vagas",
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "infra" / "migrations"


@pytest.fixture(scope="session")
def engine():
    """Engine SQLAlchemy para o banco de teste (escopo de sessão)."""
    eng = create_engine(DB_URL)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session", autouse=True)
def aplicar_migrations(engine):
    """Aplica todas as migrations SQL antes dos testes de integração."""
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with eng.connect() as conn:
        for sql_file in sql_files:
            sql = sql_file.read_text(encoding="utf-8")
            conn.execute(text(sql))
            conn.commit()
    yield


@pytest.fixture
def clean_tables(engine):
    """Limpa as tabelas de dados entre testes para isolamento."""
    yield
    with engine.begin() as conn:
        # Ordem respeitando FKs
        conn.execute(text("DELETE FROM gold.mart_vagas"))
        conn.execute(text("DELETE FROM gold.mart_salarios"))
        conn.execute(text("DELETE FROM gold.mart_demanda_tecnologias"))
        conn.execute(text("DELETE FROM gold.mart_status_fontes"))
        conn.execute(text("DELETE FROM gold.mart_qualidade_campos"))
        conn.execute(text("DELETE FROM gold.mart_vagas_por_dia"))
        conn.execute(text("DELETE FROM gold.mart_vagas_por_origem_localidade"))
        conn.execute(text("DELETE FROM silver.jobs"))
        conn.execute(text("DELETE FROM raw.job_observations"))
        conn.execute(text("DELETE FROM bronze.scrape_runs"))
        conn.commit()


@pytest.fixture
def conexao(engine, clean_tables):
    """Retorna uma conexão aberta com o banco de teste."""
    with engine.connect() as conn:
        yield conn
