"""Testes de integracao: exigem PostgreSQL (services: postgres no CI).

Marcados com @pytest.mark.integration para nao rodar no job de testes
unitarios (sem banco). Rodam apenas no job `integration` e no schedule do dbt.

Execucao local:
    DATABASE_URL=postgresql+psycopg://... pytest app/tests/test_integration.py -m integration -v
"""
from __future__ import annotations

import os
import pytest

from sqlalchemy import text

from database.connection import engine
from repositories.job_repository import JobRepository, SALVA, DUPLICADA
from schemas.job_schema import JobSchema


@pytest.fixture(scope="module")
def conexao_banco():
    """Garante que o banco esta disponível; falha o teste se nao estiver."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL nao disponivel: {exc}")
    yield


@pytest.mark.integration
def test_conexao_postgres(conexao_banco):
    """Verifica que o banco responde a uma consulta simples."""
    with engine.connect() as connection:
        resultado = connection.execute(text("SELECT 1 AS ok")).scalar()
    assert resultado == 1


@pytest.mark.integration
def test_job_repository_salva_e_deduplica(conexao_banco):
    """Integraçao: salvar duas vezes a mesma vaga => primeira SALVA, segunda DUPLICADA."""
    vaga = JobSchema(
        titulo="Engenheiro de Dados Pleno (integracao)",
        empresa="Empresa Integracao",
        senioridade="Pleno",
        localizacao="Sao Paulo - SP",
        descricao="Vaga de integracao para testar o JobRepository.",
        link="https://example.com/vaga-integracao-001",
        origem="IntegracaoTest",
        id_externo="int-001",
    )

    resultado1 = JobRepository.salvar(vaga)
    assert resultado1 == SALVA, f"Esperava SALVA, obteve {resultado1}"

    resultado2 = JobRepository.salvar(vaga)
    assert resultado2 == DUPLICADA, f"Esperava DUPLICADA, obteve {resultado2}"
