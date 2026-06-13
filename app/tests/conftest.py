"""
conftest.py — configuração global do pytest.

Por que este arquivo existe?
-----------------------------
Vários módulos do projeto importam `database.connection` no nível de módulo
(fora de funções), o que faz o SQLAlchemy tentar conectar ao PostgreSQL
assim que o arquivo é carregado — antes mesmo de qualquer teste rodar.

Nos testes unitários não temos banco disponível, então interceptamos
essas importações aqui, antes que qualquer arquivo de teste seja coletado.

O conftest.py é executado pelo pytest antes de tudo, garantindo que
os mocks estejam no lugar certo na hora certa.
"""
import sys
from unittest.mock import MagicMock

# ── Mock de database.connection ──────────────────────────────────────────────
# Substitui o módulo inteiro por um objeto fake.
# Qualquer `from database.connection import engine` ou
# `from database.connection import Sessionlocal` receberá o mock.
_mock_connection = MagicMock()
_mock_connection.engine      = MagicMock()
_mock_connection.Sessionlocal = MagicMock()

sys.modules["database.connection"] = _mock_connection

# ── Mock de database.models ───────────────────────────────────────────────────
# base.metadata.create_all() é chamado no main.py e scheduler.py.
# Sem esse mock, o import desses módulos nos testes tentaria criar tabelas.
_mock_models = MagicMock()
_mock_models.base = MagicMock()

sys.modules["database.models"] = _mock_models