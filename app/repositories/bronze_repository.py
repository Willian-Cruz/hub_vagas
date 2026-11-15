"""Persistência append-only das coletas na camada Bronze."""
from datetime import datetime, timezone
from uuid import UUID

from database.connection import SessionLocal
from database.bronze_model import ScrapeRun


class BronzeRepository:
    """Grava o estado dos scrapers na camada Bronze sem aplicar regras de negócio."""

    @staticmethod
    def persistir_resultados(
        resultados,
        run_id: UUID,
        started_at: datetime,
        finished_at: datetime | None = None,
    ) -> int:
        """Salva o status de execução de cada fonte em bronze.scrape_runs.

        Retorna quantos registros de scrape_run foram gravados.
        """
        finished_at = finished_at or datetime.now(timezone.utc)
        session = SessionLocal()

        try:
            for resultado in resultados:
                session.add(
                    ScrapeRun(
                        run_id=run_id,
                        source=resultado.source,
                        status=resultado.status.value,
                        pages_processed=resultado.pages_processed,
                        jobs_found=len(resultado.jobs),
                        error=resultado.error,
                        started_at=started_at,
                        finished_at=finished_at,
                    )
                )

            session.commit()
            return len(resultados)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
