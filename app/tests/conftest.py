"""
conftest.py — configuração global do pytest.

Por que este arquivo existe?
-----------------------------
Vários módulos do projeto importam `database.connection` no nível de módulo
(fora de funções), o que faz o SQLAlchemy tentar conectar ao PostgreSQL
assim que o arquivo é carregado — antes mesmo de qualquer teste rodar.
Pior: `settings.py` levanta RuntimeError se não houver DATABASE_URL/DB_*
configurados, o que aconteceria de cara em CI sem um .env.

Nos testes unitários não temos banco disponível, então interceptamos
essa importação aqui, antes que qualquer arquivo de teste seja coletado.

Importante: NÃO mockamos `database.models`. O módulo só contém
`base = declarative_base()` — é seguro importar de verdade, não abre
nenhuma conexão. Mocká-lo como um MagicMock() quebra silenciosamente
qualquer teste que use as classes reais (Job, Technology), porque
herdar de um MagicMock() não produz uma classe funcional em Python.

O conftest.py é executado pelo pytest antes de tudo, garantindo que
o mock esteja no lugar certo na hora certa.
"""
import sys
from unittest.mock import MagicMock

# ── Mock de database.connection ──────────────────────────────────────────────
# Substitui o módulo inteiro por um objeto fake.
# Qualquer `from database.connection import engine` ou
# `from database.connection import SessionLocal` receberá o mock.
_mock_connection = MagicMock()
_mock_connection.engine = MagicMock()
_mock_connection.SessionLocal = MagicMock()

sys.modules["database.connection"] = _mock_connection