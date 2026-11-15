"""
PipelineService — orquestra APENAS a ingestão de dados: coleta e landing zone Bronze.

Responsabilidades:
    1. Coleta vagas via CollectorService (todos os scrapers)
    2. Grava payloads e status de fontes na camada Bronze (append-only)
    3. Registra início, fim, duração e erros no log

Por que separar do main.py?
    O main.py se torna apenas um ponto de entrada manual.
    O SchedulerService chama PipelineService.executar() no horário agendado.
    Testes podem chamar PipelineService.executar() de forma controlada.

Arquitetura decoupled:
    - Ingestão (PipelineService): scrape → Bronze (landing zone)
    - Transformação (dbt): Bronze → Silver → Gold
    - Consumo: Gold → Excel / Power BI

A tabela legacy `jobs` (JobRepository) foi removida deste fluxo.
A transformação é responsibility separada, executada via `python app/transform.py`.
"""
import time
from datetime import datetime, timezone
from uuid import uuid4

from utils.logger import get_logger
from services.collector_service import CollectorService
from repositories.bronze_repository import BronzeRepository
from scrapers.base_scraper import ScrapeStatus

logger = get_logger(__name__)


class PipelineService:

    @staticmethod
    def executar() -> dict:
        """
        Executa o pipeline de ingestão: coleta e persistência na Bronze.

        Returns:
            dict com métricas da execução:
            {
                "run_id":       str,   # UUID da execução
                "coletadas":    int,   # vagas do tema retornadas pelos scrapers
                "descartadas":  int,   # vagas fora do tema, descartadas na coleta
                "bronze_salvas": int,   # observações gravadas na camada Bronze
                "bronze_ok":    bool,  # True se a Bronze foi gravada com sucesso
                "fontes":       list,  # status, contagem e erro por scraper
                "duracao_seg":  float, # tempo total em segundos
                "sucesso":      bool,  # False se a coleta ou persistência falhar
            }
        """
        logger.info("=" * 60)
        logger.info("PIPELINE DE INGESTÃO INICIADO")
        logger.info("=" * 60)

        metricas = {
            "run_id": None,
            "coletadas":   0,
            "descartadas": 0,
            "bronze_salvas": 0,
            "bronze_ok": False,
            "fontes":      [],
            "duracao_seg": 0.0,
            "sucesso":     False,
        }

        inicio = time.time()
        inicio_utc = datetime.now(timezone.utc)
        run_id = uuid4()
        metricas["run_id"] = str(run_id)

        try:
            # ── 1. Coleta ──────────────────────────────────────────────
            logger.info("Etapa 1/2: Coletando vagas...")
            resultados = CollectorService.coletar_resultados()
            metricas["fontes"] = [
                {
                    "origem": resultado.source,
                    "status": resultado.status.value,
                    "vagas": len(resultado.jobs),
                    "paginas": resultado.pages_processed,
                    "erro": resultado.error,
                    "descartadas": resultado.discarded,
                }
                for resultado in resultados
            ]
            vagas = [vaga for resultado in resultados for vaga in resultado.jobs]
            metricas["coletadas"] = len(vagas)
            metricas["descartadas"] = sum(resultado.discarded for resultado in resultados)
            logger.info(
                f"Coletadas: {len(vagas)} vagas | "
                f"Descartadas (fora do tema): {metricas['descartadas']}"
            )

            fontes_com_falha = [
                resultado
                for resultado in resultados
                if resultado.status not in (ScrapeStatus.SUCCESS, ScrapeStatus.EMPTY)
            ]
            nenhuma_fonte = not resultados
            for resultado in resultados:
                logger.info(
                    f"Fonte {resultado.source}: {resultado.status.value} | "
                    f"Vagas: {len(resultado.jobs)} | "
                    f"Páginas: {resultado.pages_processed}"
                )
                if resultado.error:
                    logger.warning(f"Fonte {resultado.source}: {resultado.error}")

            # ── 2. Bronze: landing zone (append-only) ──────────────────
            logger.info("Etapa 2/2: Gravando observações na camada Bronze...")
            bronze_ok = False
            try:
                metricas["bronze_salvas"] = BronzeRepository.persistir_resultados(
                    resultados,
                    run_id=run_id,
                    started_at=inicio_utc,
                    finished_at=datetime.now(timezone.utc),
                )
                bronze_ok = True
                metricas["bronze_ok"] = True
                logger.info(
                    "Bronze concluída — %d observação(ões)",
                    metricas["bronze_salvas"],
                )
            except Exception:
                logger.exception("Falha ao persistir a camada Bronze")

            metricas["sucesso"] = (
                bronze_ok
                and not fontes_com_falha
                and not nenhuma_fonte
            )

            if fontes_com_falha or nenhuma_fonte:
                logger.warning(
                    "Pipeline concluído com falhas em coleta ou persistência"
                )

        except Exception as e:
            logger.error(f"Erro crítico no pipeline: {e}", exc_info=True)
            metricas["sucesso"] = False

        finally:
            metricas["duracao_seg"] = round(time.time() - inicio, 2)
            status = "CONCLUÍDO" if metricas["sucesso"] else "FALHOU"
            logger.info(
                f"PIPELINE {status} em {metricas['duracao_seg']}s | "
                f"Coletadas: {metricas['coletadas']} | "
                f"Descartadas: {metricas['descartadas']} | "
                f"Bronze: {metricas['bronze_salvas']}"
            )
            logger.info("=" * 60)

        return metricas
