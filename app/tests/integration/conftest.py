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
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ── Restaurar database.connection real (o conftest raiz o mocka globalmente) ──
# Os testes de integração precisam do SQLAlchemy real conectado ao PostgreSQL.
if "database.connection" in sys.modules:
    del sys.modules["database.connection"]
from database.connection import engine as _real_engine  # noqa: F401  (garante import real)

# Carrega variáveis de ambiente do .env se existir
load_dotenv()

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
    with engine.connect() as conn:
        for sql_file in sql_files:
            sql = sql_file.read_text(encoding="utf-8")
            conn.execute(text(sql))
            conn.commit()
    yield


@pytest.fixture
def clean_tables(engine):
    """Limpa as tabelas de dados entre testes para isolamento.

    Apenas tabelas criadas pelas migrations SQL (raw e bronze) sao limpas.
    Tabelas de silver e gold sao criadas pelo dbt e nao existem apos apenas
    migrations, portanto nao devem ser alvo de limpeza aqui.
    """
    yield
    with engine.begin() as conn:
        # Ordem respeitando FKs
        conn.execute(text("DELETE FROM raw.job_observations"))
        conn.execute(text("DELETE FROM bronze.scrape_runs"))
        conn.commit()


@pytest.fixture
def conexao(engine, clean_tables):
    """Retorna uma conexão aberta com o banco de teste."""
    conn = engine.connect()
    yield conn
    conn.close()
