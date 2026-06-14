"""
settings.py — configuração central de variáveis de ambiente.

Suporta dois modos de conexão:

    Modo local (desenvolvimento):
        Define DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME no .env.
        A DATABASE_URL é montada automaticamente.

    Modo nuvem (Cloud Run + Cloud SQL):
        O Cloud Run injeta DATABASE_URL diretamente via variável de ambiente.
        Formato: postgresql://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
        As variáveis individuais são ignoradas nesse caso.
"""
from dotenv import load_dotenv
import os

load_dotenv(encoding="utf-8")

# ── Variáveis individuais (modo local) ───────────────────────────────────────
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME")

# ── DATABASE_URL — prioridade sobre variáveis individuais ────────────────────
# No Cloud Run, essa variável é injetada automaticamente pelo Secret Manager.
# Localmente, pode ser definida no .env ou montada a partir das variáveis acima.
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── GitHub Pages — URL base do dashboard publicado ───────────────────────────
# Usado pelo DashboardService para gerar links absolutos quando necessário.
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "")