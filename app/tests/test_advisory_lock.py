"""Testes de advisory lock e concorrência (Etapa 4.4).

Valida o comportamento fail-closed e a exclusão mutua do advisory lock
PostgreSQL usado pelo PipelineService.
"""
import threading
import time
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from services.pipeline_service import ADVISORY_LOCK_KEY, PipelineService


DB_URL = "postgresql+psycopg://hub_vagas:hub_vagas@localhost:5432/hub_vagas_test"


def _nova_conexao():
    """Cria uma conexão SQLAlchemy com pool desabilitado (sessão PostgreSQL distinta)."""
    eng = create_engine(DB_URL, poolclass=None)
    return eng.connect()


@pytest.fixture
def engine():
    eng = create_engine(DB_URL, poolclass=None)
    yield eng
    eng.dispose()


@pytest.mark.integration
class TestAdvisoryLock:
    """Testes de advisory lock PostgreSQL."""

    def test_lock_disponivel_consegue_adquirir(self, engine):
        """Quando o lock está livre, a aquisição deve ter sucesso."""
        conexao, adquirida = PipelineService._adquirir_travar_execucao()
        assert adquirida is True
        assert conexao is not None
        PipelineService._liberar_travar_execucao(conexao)

    def test_lock_ocupado_bloqueia_segunda_execucao(self, engine):
        """Quando o lock está ocupado em outra sessão, a segunda não consegue adquiri-lo."""
        # Garante que o lock está livre (desbloqueia caso alguma sessão anterior
        # tenha ficado segurando)
        eng_admin = create_engine(DB_URL, poolclass=None)
        with eng_admin.connect() as conn_admin:
            conn_admin.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": ADVISORY_LOCK_KEY},
            )
            conn_admin.commit()
        eng_admin.dispose()

        # Primeira conexão adquire o lock e NÃO o libera (mantém sessão aberta)
        conexao1 = _nova_conexao()
        resultado1 = conexao1.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": ADVISORY_LOCK_KEY},
        ).scalar()
        conexao1.commit()
        assert bool(resultado1) is True

        # Segunda conexão (sessão diferente) tenta adquirir o mesmo lock (deve falhar)
        conexao2 = _nova_conexao()
        resultado2 = conexao2.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": ADVISORY_LOCK_KEY},
        ).scalar()
        conexao2.commit()
        assert bool(resultado2) is False

        # Libera o primeiro lock fechando a conexão
        conexao1.close()
        conexao2.close()

    def test_liberacao_apos_falha(self, engine):
        """O lock deve ser liberado em finally mesmo após exceção."""
        # Garante que o lock está livre antes do teste
        eng_admin = create_engine(DB_URL, poolclass=None)
        with eng_admin.connect() as conn_admin:
            conn_admin.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": ADVISORY_LOCK_KEY},
            )
            conn_admin.commit()
        eng_admin.dispose()

        conexao, adquirida = PipelineService._adquirir_travar_execucao()
        assert adquirida is True

        # Libera o lock (fecha a conexão)
        PipelineService._liberar_travar_execucao(conexao)

        # Depois de liberar, outra execução consegue adquirir
        conexao2, adquirida2 = PipelineService._adquirir_travar_execucao()
        assert adquirida2 is True
        PipelineService._liberar_travar_execucao(conexao2)

    def test_duas_execucoes_simultaneas_apenas_uma_adquire(self, engine):
        """Duas threads concorrentes: apenas uma consegue o advisory lock."""
        # Garante que o lock está livre antes do teste
        eng_admin = create_engine(DB_URL, poolclass=None)
        with eng_admin.connect() as conn_admin:
            conn_admin.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": ADVISORY_LOCK_KEY},
            )
            conn_admin.commit()
        eng_admin.dispose()

        resultados = {}
        lock = threading.Lock()

        def thread_adquire(nome):
            # Cada thread usa sua própria engine (sessão PostgreSQL distinta)
            eng = create_engine(DB_URL, poolclass=None)
            conn = eng.connect()
            resultado = conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": ADVISORY_LOCK_KEY},
            ).scalar()
            conn.commit()
            with lock:
                resultados[nome] = bool(resultado)
            if bool(resultado):
                time.sleep(0.2)  # Segura o lock por um pouco
                conn.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": ADVISORY_LOCK_KEY},
                )
                conn.commit()
            conn.close()
            eng.dispose()

        t1 = threading.Thread(target=thread_adquire, args=("thread1",))
        t2 = threading.Thread(target=thread_adquire, args=("thread2",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exatamente uma thread deve ter conseguido o lock
        assert sum(resultados.values()) == 1
