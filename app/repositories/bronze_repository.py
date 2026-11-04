"""Persistência append-only das coletas na camada Bronze."""
import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from database.connection import SessionLocal
from database.bronze_model import JobObservation, ScrapeRun


class BronzeRepository:
    """Grava observações e o estado dos scrapers sem aplicar regras de negócio."""

    @staticmethod
    def persistir_resultados(
        resultados,
        run_id: UUID,
        started_at: datetime,
        finished_at: datetime | None = None,
    ) -> int:
        """Salva uma observação por vaga e retorna quantas foram registradas.

        O payload contém a saída original do contrato de cada scraper, antes
        da normalização de senioridade, localidade, salário e tecnologias.
        Cada execução cria novas observações para preservar o histórico.
        """
        finished_at = finished_at or datetime.now(timezone.utc)
        session = SessionLocal()
        observacoes = []

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

                for vaga in resultado.jobs:
                    payload = {
                        "schema_version": 1,
                        "job": vaga.model_dump(mode="json"),
                        "source_payload": vaga.raw_payload,
                    }
                    hash_json = json.dumps(
                        {"schema_version": 1, "job": payload["job"]},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    observacoes.append(
                        JobObservation(
                            run_id=run_id,
                            source=resultado.source,
                            source_job_id=vaga.link,
                            collected_at=finished_at,
                            payload_hash=hashlib.sha256(
                                hash_json.encode("utf-8")
                            ).hexdigest(),
                            raw_payload=payload,
                        )
                    )

            session.add_all(observacoes)
            session.commit()
            return len(observacoes)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
