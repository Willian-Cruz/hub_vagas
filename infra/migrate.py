"""Script de aplicacao de migrações SQL versionadas.

Lê os arquivos SQL de infra/migrations/, consulta a tabela
public.schema_migrations para saber quais já foram aplicadas e executa
apenas as pendentes, em ordem numerica.

Uso:
    python infra/migrate.py               # aplica pendentes
    python infra/migrate.py --verificar   # lista pendentes sem aplicar

Variáveis de ambiente:
    DATABASE_URL  (via .env, carregado por python-dotenv)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def engine_para_banco():
    from config.settings import DATABASE_URL

    url = DATABASE_URL
    if isinstance(url, str) and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return create_engine(url, pool_pre_ping=True)


def arquivos_migracao():
    """Devolve arquivos .sql ordenados pelo nome (001, 002, ...)."""
    return sorted(
        p for p in MIGRATIONS_DIR.glob("*.sql") if p.name[0:4].isdigit()
    )


def checksum(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def tabela_existe(engine) -> bool:
    with engine.connect() as connection:
        resultado = connection.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'schema_migrations'"
            )
        ).scalar()
        return bool(resultado)


def garantir_tabela_controle(engine):
    """Cria public.schema_migrations se ainda nao existir."""
    if not tabela_existe(engine):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE public.schema_migrations (
                        arquivo            TEXT PRIMARY KEY,
                        aplicado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
                        checksum_sha256    TEXT NOT NULL
                    )
                    """
                )
            )


def migrações_aplicadas(engine) -> dict[str, str]:
    """Devolve {arquivo: checksum} das migrações já registradas."""
    with engine.connect() as connection:
        linhas = connection.execute(
            text("SELECT arquivo, checksum_sha256 FROM public.schema_migrations")
        ).fetchall()
    return {arquivo: checksum for arquivo, checksum in linhas}


def aplicar_migracao(engine, caminho: Path) -> None:
    """Executa um arquivo SQL e registra na tabela de controle."""
    sql = caminho.read_text(encoding="utf-8")
    soma = checksum(sql)

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(
            text(
                """
                INSERT INTO public.schema_migrations (arquivo, aplicado_em, checksum_sha256)
                VALUES (:arquivo, :aplicado_em, :checksum)
                ON CONFLICT (arquivo) DO UPDATE
                    SET aplicado_em = EXCLUDED.aplicado_em,
                        checksum_sha256 = EXCLUDED.checksum_sha256
                """
            ),
            {
                "arquivo": caminho.name,
                "aplicado_em": datetime.now(timezone.utc),
                "checksum": soma,
            },
        )


def main():
    parser = argparse.ArgumentParser(
        description="Aplica migrações SQL pendentes de infra/migrations/"
    )
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="Apenas lista quais migrações seriam aplicadas (nao executa)",
    )
    args = parser.parse_args()

    engine = engine_para_banco()
    garantir_tabela_controle(engine)

    aplicadas = migrações_aplicadas(engine)
    pendentes = [
        a for a in arquivos_migracao() if a.name not in aplicadas
    ]

    if not pendentes:
        print("Nenhuma migração pendente. Banco está em dia.")
        return 0

    print(f"{len(pendentes)} migração(ões) pendente(s):")
    for p in pendentes:
        ja_aplicada = p.name in aplicadas
        marcador = " (ja aplicada)" if ja_aplicada else ""
        print(f"  - {p.name}{marcador}")

    if args.verificar:
        print("\nModo --verificar: nenhuma alteração foi feita.")
        return 0

    for p in pendentes:
        print(f"\nAplicando {p.name} ...")
        aplicar_migracao(engine, p)
        print(f"  OK: {p.name} aplicada.")

    print("\nTodas as migrações pendentes foram aplicadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
