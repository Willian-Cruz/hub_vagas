import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from database.connection import SessionLocal
from utils.logger import get_logger

logger = get_logger(__name__)

# Resultados possíveis de JobRepository.salvar().
# O PipelineService usa esses valores para montar as métricas da execução.
SALVA = "salva"
DUPLICADA = "duplicada"
ERRO = "erro"

# Timeout (segundos) além do qual uma observação idêntica já gravada é
# considerada duplicata e não insere uma nova linha em raw.job_observations.
# A tabela é append-only: a dedup evita guardar o mesmo payload duas vezes.


def _payload_hash(raw_payload: dict) -> str:
    """Hash estável do payload bruto para detectar retransmissões idênticas."""
    canonical = json.dumps(raw_payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _raw_payload_de_vaga(vaga) -> dict:
    """Constrói o payload bruto (JSONB) a ser guardado em raw.job_observations.

    Guarda os campos exatamente como vieram do scraper, sem qualquer
    normalização de negócio (senioridade, local, salário, modalidade,
    tecnologias ficam para o dbt).
    """
    campos = {
        "titulo": vaga.titulo,
        "empresa": vaga.empresa,
        "senioridade": vaga.senioridade,
        "localizacao": vaga.localizacao,
        "descricao": vaga.descricao,
        "salario": vaga.salario,
        "link": vaga.link,
        "origem": vaga.origem,
        "id_externo": vaga.id_externo,
        "data_publicacao": (
            vaga.data_publicacao.isoformat() if vaga.data_publicacao else None
        ),
        "modalidade": vaga.modalidade,
        "experiencia": vaga.experiencia,
        "escolaridade": vaga.escolaridade,
        "qtd_posicoes": vaga.qtd_posicoes,
    }
    # Mescla o fragmento original (ex.: HTML do card) quando o scraper o traz.
    if vaga.raw_payload:
        campos["_raw_payload_scraper"] = vaga.raw_payload
    return campos


class JobRepository:

    @staticmethod
    def salvar(vaga, run_id: UUID | None = None) -> str:
        """
        Persiste o payload bruto da vaga em `raw.job_observations` (append-only).

        Não aplica normalização de negócio (senioridade, local, salário,
        modalidade, tecnologias): isso cabe ao dbt (staging → Silver).

        A dedup é feita por (origem, id_externo) + payload_hash: se a última
        observação da mesma vaga no portal tiver o mesmo payload, não insere
        novamente e devolve DUPLICADA.

        Returns:
            "salva"      — nova observação inserida
            "duplicada"  — payload idêntico já existe para essa vaga/fonte
            "erro"       — falha ao persistir (rollback)
        """
        run_id = run_id or uuid4()
        origem = vaga.origem
        source_job_id = vaga.id_externo
        collected_at = datetime.now(timezone.utc)

        raw_payload = _raw_payload_de_vaga(vaga)
        payload_hash = _payload_hash(raw_payload)

        session = SessionLocal()

        try:
            # ── Dedup: mesmo payload já gravado para esta vaga/fonte? ────
            existente = session.execute(
                text(
                    """
                    SELECT payload_hash
                    FROM raw.job_observations
                    WHERE source = :source
                      AND source_job_id IS NOT DISTINCT FROM :source_job_id
                    ORDER BY collected_at DESC
                    LIMIT 1
                    """
                ),
                {"source": origem, "source_job_id": source_job_id},
            ).fetchone()

            if existente is not None and existente[0] == payload_hash:
                logger.info(
                    "Observação duplicada (mesmo payload) | fonte=%s source_job_id=%s",
                    origem, source_job_id,
                )
                return DUPLICADA

            # ── Insere nova observação bruta ─────────────────────────────
            session.execute(
                text(
                    """
                    INSERT INTO raw.job_observations
                        (run_id, source, source_job_id, collected_at,
                         payload_hash, raw_payload, is_relevant)
                    VALUES
                        (:run_id, :source, :source_job_id, :collected_at,
                         :payload_hash, :raw_payload::jsonb, :is_relevant)
                    """
                ),
                {
                    "run_id": run_id,
                    "source": origem,
                    "source_job_id": source_job_id,
                    "collected_at": collected_at,
                    "payload_hash": payload_hash,
                    "raw_payload": json.dumps(raw_payload, ensure_ascii=False),
                    "is_relevant": True,
                },
            )
            session.commit()

            logger.info(
                "Salva raw.job_observations: %s | fonte=%s | hash=%s",
                vaga.titulo, origem, payload_hash[:12],
            )
            return SALVA

        except IntegrityError as erro:
            session.rollback()
            logger.info("Violação de integridade ao salvar vaga %s: %s", vaga.link, erro)
            return DUPLICADA

        except Exception:
            session.rollback()
            logger.exception("Erro inesperado ao salvar vaga %s", vaga.link)
            return ERRO

        finally:
            session.close()
