"""
settings.py — configuração central de variáveis de ambiente.

Define DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME no .env.
A DATABASE_URL é montada automaticamente a partir dessas variáveis,
ou pode ser definida diretamente via DATABASE_URL.
"""

from dotenv import load_dotenv
import os

load_dotenv(encoding="utf-8")

# ── Variáveis individuais ────────────────────────────────────────────────────
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# ── DATABASE_URL — prioridade sobre variáveis individuais ────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:

    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):

        raise RuntimeError("Configure DATABASE_URL " "ou as variáveis DB_*.")

    DATABASE_URL = (
        f"postgresql://"
        f"{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}"
        f"/{DB_NAME}"
    )
