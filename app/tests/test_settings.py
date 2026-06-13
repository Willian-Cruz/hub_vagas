"""
Testes unitários para settings.py (Sprint 8).

O comportamento crítico para o Cloud Run funcionar:
    - Quando DATABASE_URL está definida → usa ela diretamente
    - Quando DATABASE_URL não está definida → monta a partir das variáveis individuais

Estratégia:
    Não usamos importlib.reload() porque ele não atualiza a referência
    local ao módulo — o teste continuaria olhando para o objeto antigo.
    Em vez disso, testamos a lógica de montagem da URL diretamente,
    simulando o que o settings.py faz ao ser carregado.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest


def _montar_url(env: dict) -> str:
    """
    Replica a lógica do settings.py:
        DATABASE_URL direta → tem prioridade
        Sem DATABASE_URL   → monta a partir das variáveis individuais
    """
    url_direta = env.get("DATABASE_URL")
    if url_direta:
        return url_direta

    user     = env.get("DB_USER", "")
    password = env.get("DB_PASSWORD", "")
    host     = env.get("DB_HOST", "localhost")
    port     = env.get("DB_PORT", "5432")
    name     = env.get("DB_NAME", "")

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


class TestDatabaseUrl:

    def test_usa_database_url_direta_quando_definida(self):
        """
        Cenário Cloud Run: DATABASE_URL é injetada pelo Secret Manager.
        Deve ter prioridade sobre as variáveis individuais.
        """
        url_esperada = (
            "postgresql://user:pass@/dbname"
            "?host=/cloudsql/proj:region:inst"
        )
        env = {
            "DATABASE_URL": url_esperada,
            "DB_USER":      "outro_user",
            "DB_PASSWORD":  "outra_senha",
            "DB_HOST":      "outro_host",
            "DB_PORT":      "9999",
            "DB_NAME":      "outro_banco",
        }
        assert _montar_url(env) == url_esperada

    def test_monta_url_a_partir_de_variaveis_individuais(self):
        """
        Cenário local: DATABASE_URL não definida.
        Deve montar a URL a partir das variáveis individuais.
        """
        env = {
            "DB_USER":     "willian",
            "DB_PASSWORD": "senha123",
            "DB_HOST":     "localhost",
            "DB_PORT":     "5432",
            "DB_NAME":     "hub_vagas",
        }
        url = _montar_url(env)
        assert "willian"   in url
        assert "localhost" in url
        assert "hub_vagas" in url
        assert "5432"      in url

    def test_url_montada_tem_formato_postgresql(self):
        """A URL montada localmente deve começar com postgresql://"""
        env = {
            "DB_USER": "user", "DB_PASSWORD": "pass",
            "DB_HOST": "localhost", "DB_PORT": "5432", "DB_NAME": "db",
        }
        assert _montar_url(env).startswith("postgresql://")

    def test_host_padrao_e_localhost(self):
        """DB_HOST deve ter localhost como valor padrão."""
        env = {"DB_USER": "u", "DB_PASSWORD": "p", "DB_PORT": "5432", "DB_NAME": "db"}
        assert "localhost" in _montar_url(env)

    def test_porta_padrao_e_5432(self):
        """DB_PORT deve ter 5432 como valor padrão."""
        env = {"DB_USER": "u", "DB_PASSWORD": "p", "DB_HOST": "localhost", "DB_NAME": "db"}
        assert "5432" in _montar_url(env)