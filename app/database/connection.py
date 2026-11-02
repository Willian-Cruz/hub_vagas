from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from config.settings import DATABASE_URL, DB_HOST, LOCAL_DATABASE_CONFIG


if isinstance(DATABASE_URL, str):
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    url = make_url(DATABASE_URL)
    if url.drivername in ("postgresql", "postgresql+psycopg2"):
        DATABASE_URL = url.set(drivername="postgresql+psycopg")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def ensure_local_database_exists() -> bool:
    """Cria o banco local configurado se ele ainda não existir.

    Retorna True somente quando criou o banco. Bancos remotos e URLs explícitas
    ficam sob responsabilidade do serviço de hospedagem.
    """
    if not LOCAL_DATABASE_CONFIG:
        return False

    host = (engine.url.host or DB_HOST or "localhost").lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        return False

    database_name = engine.url.database
    if not database_name:
        return False

    admin_engine = create_engine(
        engine.url.set(database="postgres"),
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
    )

    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            ).scalar()

            if exists:
                return False

            safe_name = connection.dialect.identifier_preparer.quote(database_name)
            connection.exec_driver_sql(f"CREATE DATABASE {safe_name}")
            return True
    finally:
        admin_engine.dispose()
