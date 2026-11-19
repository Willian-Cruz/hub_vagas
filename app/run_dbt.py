"""Executa o CLI do dbt usando as credenciais do .env do projeto.

Exemplos:
    python app/run_dbt.py debug
    python app/run_dbt.py build
    python app/run_dbt.py source freshness
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

from utils.logger import get_logger, log_event


logger = get_logger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT_DIR / "dbt"
DBT_PROFILE = DBT_DIR / "profiles.yml"
DBT_PROFILE_TEMPLATE = DBT_DIR / "profiles.yml.example"


def _configurar_variaveis_dbt() -> None:
    load_dotenv(ROOT_DIR / ".env", encoding="utf-8")

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        url = make_url(database_url)
        valores = {
            "DBT_HOST": url.host or url.query.get("host") or "localhost",
            "DBT_USER": url.username,
            "DBT_PASSWORD": url.password,
            "DBT_PORT": str(url.port or 5432),
            "DBT_DATABASE": url.database,
            "DBT_SSLMODE": str(url.query.get("sslmode", "prefer")),
        }
    else:
        valores = {
            "DBT_HOST": os.getenv("DB_HOST", "localhost"),
            "DBT_USER": os.getenv("DB_USER"),
            "DBT_PASSWORD": os.getenv("DB_PASSWORD"),
            "DBT_PORT": os.getenv("DB_PORT", "5432"),
            "DBT_DATABASE": os.getenv("DB_NAME"),
            "DBT_SSLMODE": os.getenv("DB_SSLMODE", "prefer"),
        }

    for chave, valor in valores.items():
        if valor is not None:
            os.environ.setdefault(chave, valor)
    os.environ.setdefault("DBT_SCHEMA", "public")


def main(argv: list[str] | None = None) -> int:
    argumentos = list(argv if argv is not None else sys.argv[1:])
    if not argumentos:
        argumentos = ["build"]

    _configurar_variaveis_dbt()
    executavel = shutil.which("dbt")
    if not executavel:
        # Fallback para Windows Store Python (local-packages/Scripts)
        import site

        for site_dir in site.getusersitepackages().split(os.pathsep):
            scripts_dir = os.path.join(os.path.dirname(site_dir), "Scripts")
            candidato = os.path.join(scripts_dir, "dbt.exe")
            if os.path.isfile(candidato):
                executavel = candidato
                break
    if not executavel:
        print(
            "CLI dbt não encontrado. Ative o venv e instale requirements.txt.",
            file=sys.stderr,
        )
        return 127

    if not DBT_PROFILE.exists():
        shutil.copyfile(DBT_PROFILE_TEMPLATE, DBT_PROFILE)

    run_id = os.getenv("RUN_ID", "manual")
    subcomando = argumentos[0] if argumentos else "build"

    log_event(
        logger=logger,
        level="INFO",
        run_id=run_id,
        component="dbt",
        stage="transformacao",
        event="dbt_started",
        status="iniciado",
        mensagem=f"dbt {subcomando} iniciado",
    )

    inicio_dbt = time.time()
    # --project-dir e --profiles-dir são opções do subcomando (dbt build ...),
    # não do dbt em si: antes do subcomando o dbt responde "No such option".
    comando = [
        executavel,
        *argumentos,
        "--project-dir",
        str(DBT_DIR),
        "--profiles-dir",
        str(DBT_DIR),
    ]
    resultado = subprocess.run(comando, cwd=ROOT_DIR, check=False)
    duracao_dbt = round(time.time() - inicio_dbt, 2)
    codigo_retorno = resultado.returncode

    if codigo_retorno == 0:
        log_event(
            logger=logger,
            level="INFO",
            run_id=run_id,
            component="dbt",
            stage="transformacao",
            event="dbt_completed",
            status="sucesso",
            duration_ms=round(duracao_dbt * 1000, 2),
            mensagem=f"dbt {subcomando} concluído com sucesso em {duracao_dbt}s",
        )
    else:
        log_event(
            logger=logger,
            level="ERROR",
            run_id=run_id,
            component="dbt",
            stage="transformacao",
            event="dbt_failed",
            status="falha",
            duration_ms=round(duracao_dbt * 1000, 2),
            mensagem=f"dbt {subcomando} falhou com código {codigo_retorno} após {duracao_dbt}s",
        )

    return codigo_retorno


if __name__ == "__main__":
    raise SystemExit(main())
