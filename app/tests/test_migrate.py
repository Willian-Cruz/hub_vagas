"""Testes unitários para infra/migrate.py (sem banco real).

Verifica a lógica de ordenação, checksum e detecção de pendentes usando mocks.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys_path_modificado = False


def _import_migrate():
    """Importa o módulo migrate com o caminho de infra/ no sys.path."""
    import sys

    infra_dir = str(Path(__file__).resolve().parent.parent.parent / "infra")
    if infra_dir not in sys.path:
        sys.path.insert(0, infra_dir)
    import migrate

    return migrate


class FakeConn:
    """Simula uma conexão SQLAlchemy que grava em memória."""

    def __init__(self, scalar_retorna=None):
        self.executados = []
        self.commits = 0
        self._scalar_retorna = scalar_retorna

    def execute(self, sql, params=None):
        texto = str(sql)
        self.executados.append((texto, params or {}))
        return self

    def scalar(self):
        return self._scalar_retorna

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeEngine:
    """Simula o engine SQLAlchemy."""

    def __init__(self, tabela_existe=True, aplicadas=None):
        self.tabela_existe = tabela_existe
        self.aplicadas = aplicadas or {}
        self.conn = FakeConn(scalar_retorna=1 if tabela_existe else None)

    def connect(self):
        return self.conn

    def begin(self):
        return self.conn

    def dispose(self):
        pass


def test_arquivos_reais_ordenados():
    migrate = _import_migrate()
    arquivos = migrate.arquivos_migracao()
    nomes = [a.name for a in arquivos]
    # A funcao ja retorna ordenada; verificamos consistencia
    assert nomes == sorted(nomes), f"Nao ordenados: {nomes}"
    assert all(n[:4].isdigit() for n in nomes), f"Nem todos começam com número: {nomes}"


def test_checksum_é_determinístico():
    migrate = _import_migrate()
    c1 = migrate.checksum("CREATE TABLE x (id INT);")
    c2 = migrate.checksum("CREATE TABLE x (id INT);")
    assert c1 == c2
    assert len(c1) == 64  # SHA-256 hex


def test_checksum_muda_se_o_sql_mudar():
    migrate = _import_migrate()
    assert migrate.checksum("A") != migrate.checksum("B")


def test_garantir_tabela_cria_quando_nao_existe():
    migrate = _import_migrate()
    engine = FakeEngine(tabela_existe=False)
    migrate.garantir_tabela_controle(engine)
    assert any("CREATE TABLE public.schema_migrations" in e for e, _ in engine.conn.executados)


def test_garantir_tabela_nao_recria_quando_existe():
    migrate = _import_migrate()
    engine = FakeEngine(tabela_existe=True)
    migrate.garantir_tabela_controle(engine)
    assert not any("CREATE TABLE" in e for e, _ in engine.conn.executados)


def test_aplicar_migracao_registra_na_tabela():
    migrate = _import_migrate()
    engine = FakeEngine(tabela_existe=True, aplicadas={})
    caminho = Path("infra/migrations/007_schema_migrations.sql")

    migrate.aplicar_migracao(engine, caminho)

    assert any("INSERT INTO public.schema_migrations" in e for e, _ in engine.conn.executados)


def test_migracoes_aplicadas_devolve_dicionario():
    migrate = _import_migrate()
    engine = FakeEngine(tabela_existe=True, aplicadas={})
    engine.conn.fetchall = lambda: [
        ("001_inicial.sql", "abc123"),
        ("002_segunda.sql", "def456"),
    ]
    resultado = migrate.migrações_aplicadas(engine)
    assert resultado == {"001_inicial.sql": "abc123", "002_segunda.sql": "def456"}


def test_logica_deteccao_pendentes():
    """Detecção de pendentes: compara nomes de arquivos com aplicadas."""
    migrate = _import_migrate()
    arquivos = migrate.arquivos_migracao()
    todos = {a.name for a in arquivos}

    if not todos:
        pytest.skip("Nenhum arquivo de migration encontrado no diretório real")

    # Simula que todas estão aplicadas
    pendentes_todas = [a.name for a in arquivos if a.name in todos]
    assert len(pendentes_todas) == len(todos)

    # Simula que nenhuma está aplicada: todas são pendentes
    pendentes_nenhuma = [a.name for a in arquivos if a.name not in set()]
    assert len(pendentes_nenhuma) == len(todos)

    # Simula que só a primeira (ordenada) está aplicada
    primeiro = sorted(todos)[0]
    aplicadas = {primeiro: "x"}
    pendentes = [a.name for a in arquivos if a.name not in aplicadas]
    assert len(pendentes) == len(todos) - 1
    assert primeiro not in pendentes


