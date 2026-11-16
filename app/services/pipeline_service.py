"""
PipelineService — orquestra APENAS a ingestão de dados: coleta e raw layer `jobs`.

Responsabilidades:
    1. Coleta vagas via CollectorService (todos os scrapers)
    2. Grava vagas na tabela raw `jobs` (dedup por link / origem+id_externo)
    3. Registra status de cada fonte em bronze.scrape_runs para monitoramento
    4. Registra início, fim, duração e erros no log

Por que separar do main.py?
    O main.py se torna apenas um ponto de entrada manual.
    O SchedulerService chama PipelineService.executar() no horário agendado.
    Testes podem chamar PipelineService.executar() de forma controlada.

Arquitetura medallion decoupled:
    - Raw (tabela jobs): scrape direto, dedup básica por link/origem+id_externo
    - Bronze (dbt): snapshot imutável a partir da raw (append-only)
    - Silver (dbt): normalização, deduplicação avançada a partir do Bronze
    - Gold (dbt): marts analíticos a partir do Silver
    - Consumo: Gold → Excel / Power BI

A transformação é responsabilidade separada, executada via `python app/transform.py`.
"""
import time
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from utils.logger import get_logger
from services.collector_service import CollectorService
from repositories.bronze_repository import BronzeRepository
from repositories.job_repository import DUPLICADA, ERRO, JobRepository, SALVA
from scrapers.base_scraper import ScrapeStatus

logger = get_logger(__name__)


class PipelineService:

    @staticmethod
    def executar() -> dict:
        """
        Executa o pipeline de ingestão: coleta e persistência na raw layer `jobs`.

        Returns:
            dict com métricas da execução:
            {
                "run_id":            str,   # UUID da execução
                "coletadas":         int,   # vagas do tema retornadas pelos scrapers
                "descartadas":       int,   # vagas fora do tema, descartadas na coleta
                "raw_salvas":        int,   # vagas inseridas na tabela raw `jobs`
                "raw_duplicadas":    int,   # vagas ignoradas por já existirem
                "raw_erros":         int,   # vagas que falharam ao salvar
                "bronze_ok":         bool,  # True se os ScrapeRuns foram gravados
                "fontes":            list,  # status, contagem e erro por scraper
                "fontes_sucesso":    int,   # fontes com status SUCCESS
                "fontes_parcial":    int,   # fontes com status PARTIAL
                "fontes_falha":      int,   # fontes com status FAILED
                "fontes_vazio":      int,   # fontes com status EMPTY
                "duracao_seg":       float, # tempo total em segundos
                "sucesso":           bool,  # True se pelo menos uma fonte trouxe vagas
            }
        """
        logger.info("=" * 60)
        logger.info("PIPELINE DE INGESTÃO INICIADO")
        logger.info("=" * 60)

        metricas = {
            "run_id": None,
            "coletadas":      0,
            "descartadas":    0,
            "raw_salvas":     0,
            "raw_duplicadas": 0,
            "raw_erros":      0,
            "bronze_ok":      False,
            "fontes":         [],
            "fontes_sucesso": 0,
            "fontes_parcial": 0,
            "fontes_falha":   0,
            "fontes_vazio":   0,
            "duracao_seg":    0.0,
            "sucesso":        False,
        }

        inicio = time.time()
        inicio_utc = datetime.now(timezone.utc)
        run_id = uuid4()
        metricas["run_id"] = str(run_id)

        try:
            # ── 1. Coleta ──────────────────────────────────────────────
            logger.info("Etapa 1/3: Coletando vagas...")
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

            fontes_sucesso = []
            fontes_parcial = []
            fontes_falha = []
            fontes_vazio = []
            for resultado in resultados:
                logger.info(
                    f"Fonte {resultado.source}: {resultado.status.value} | "
                    f"Vagas: {len(resultado.jobs)} | "
                    f"Páginas: {resultado.pages_processed}"
                )
                if resultado.error:
                    logger.warning(f"Fonte {resultado.source}: {resultado.error}")

                if resultado.status == ScrapeStatus.SUCCESS:
                    fontes_sucesso.append(resultado)
                elif resultado.status == ScrapeStatus.PARTIAL:
                    fontes_parcial.append(resultado)
                elif resultado.status == ScrapeStatus.FAILED:
                    fontes_falha.append(resultado)
                elif resultado.status == ScrapeStatus.EMPTY:
                    fontes_vazio.append(resultado)

            metricas["fontes_sucesso"] = len(fontes_sucesso)
            metricas["fontes_parcial"] = len(fontes_parcial)
            metricas["fontes_falha"] = len(fontes_falha)
            metricas["fontes_vazio"] = len(fontes_vazio)

            # ── 2. Raw layer: salvar na tabela `jobs` ────────────────────
            logger.info("Etapa 2/3: Gravando vagas na raw layer `jobs`...")
            try:
                for vaga in vagas:
                    resultado_salvamento = JobRepository.salvar(vaga)
                    if resultado_salvamento == SALVA:
                        metricas["raw_salvas"] += 1
                    elif resultado_salvamento == DUPLICADA:
                        metricas["raw_duplicadas"] += 1
                    else:
                        metricas["raw_erros"] += 1
                logger.info(
                    "Raw concluída — %d salvas, %d duplicadas, %d erros",
                    metricas["raw_salvas"],
                    metricas["raw_duplicadas"],
                    metricas["raw_erros"],
                )
            except Exception:
                logger.exception("Falha ao persistir na raw layer `jobs`")

            # ── 3. Bronze: registro de execução por fonte ────────────────
            logger.info("Etapa 3/3: Gravando status de execução no Bronze...")
            bronze_ok = False
            try:
                metricas_bronze = BronzeRepository.persistir_resultados(
                    resultados,
                    run_id=run_id,
                    started_at=inicio_utc,
                    finished_at=datetime.now(timezone.utc),
                )
                bronze_ok = True
                metricas["bronze_ok"] = True
                logger.info(
                    "Bronze concluída — %d scrape_run(s) registrado(s)",
                    metricas_bronze,
                )
            except Exception:
                logger.exception("Falha ao persistir status no Bronze")

            # Sucesso = pelo menos uma fonte trouxe vagas (SUCCESS ou PARTIAL com vagas)
            # e a persistência no Bronze funcionou
            fontes_com_vagas = fontes_sucesso + [f for f in fontes_parcial if f.jobs]
            metricas["sucesso"] = bronze_ok and len(fontes_com_vagas) > 0

            if metricas["fontes_falha"] > 0:
                logger.warning(
                    f"Pipeline concluído com {metricas['fontes_falha']} fonte(s) em falha"
                )
            if metricas["fontes_parcial"] > 0:
                logger.info(
                    f"Pipeline concluído com {metricas['fontes_parcial']} fonte(s) parcial(is)"
                )
            if not metricas["sucesso"]:
                logger.warning(
                    "Pipeline não coletou vagas de nenhuma fonte"
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
                f"Raw: {metricas['raw_salvas']} salvas / "
                f"{metricas['raw_duplicadas']} dup / {metricas['raw_erros']} err | "
                f"Fontes: {metricas['fontes_sucesso']} ok, {metricas['fontes_parcial']} parcial, {metricas['fontes_falha']} falha, {metricas['fontes_vazio']} vazio"
            )
            logger.info("=" * 60)

        return metricas