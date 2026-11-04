"""
PipelineService — orquestra uma execução completa do pipeline.

Responsabilidades:
    1. Coleta vagas via CollectorService (todos os scrapers)
    2. Persiste cada vaga via JobRepository (com normalização)
    3. Registra início, fim, duração e erros no log

Por que separar do main.py?
    O main.py se torna apenas um ponto de entrada manual.
    O SchedulerService chama PipelineService.executar() no horário agendado.
    Testes podem chamar PipelineService.executar() de forma controlada.
    Nenhuma lógica duplicada.
"""
import time
from utils.logger import get_logger
from services.collector_service import CollectorService
from repositories.job_repository import JobRepository
from scrapers.base_scraper import ScrapeStatus

logger = get_logger(__name__)


class PipelineService:

    @staticmethod
    def executar() -> dict:
        """
        Executa o pipeline completo de coleta e persistência.

        Returns:
            dict com métricas da execução:
            {
                "coletadas":   int,   # vagas do tema retornadas pelos scrapers
                "descartadas": int,   # vagas fora do tema, descartadas na coleta
                "salvas":      int,   # vagas efetivamente inseridas no banco
                "duplicadas":  int,   # vagas ignoradas por já existirem
                "erros":       int,   # vagas que falharam ao salvar
                "fontes":      list,  # status, contagem e erro por scraper
                "duracao_seg": float, # tempo total em segundos
                "sucesso":     bool,  # False se a coleta ou persistência falhar
            }
        """
        logger.info("=" * 60)
        logger.info("PIPELINE INICIADO")
        logger.info("=" * 60)

        metricas = {
            "coletadas":   0,
            "descartadas": 0,
            "salvas":      0,
            "duplicadas":  0,
            "erros":       0,
            "fontes":      [],
            "duracao_seg": 0.0,
            "sucesso":     False,
        }

        inicio = time.time()

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

            # ── 2. Persistência ────────────────────────────────────────
            logger.info("Etapa 2/2: Persistindo no banco...")

            for vaga in vagas:
                resultado = JobRepository.salvar(vaga)

                if resultado == "salva":
                    metricas["salvas"] += 1
                elif resultado == "duplicada":
                    metricas["duplicadas"] += 1
                else:
                    metricas["erros"] += 1

            logger.info(
                f"Persistência concluída — "
                f"Salvas: {metricas['salvas']} | "
                f"Duplicadas: {metricas['duplicadas']} | "
                f"Erros: {metricas['erros']}"
            )

            metricas["sucesso"] = (
                metricas["erros"] == 0 and not fontes_com_falha and not nenhuma_fonte
            )

            if metricas["erros"] or fontes_com_falha or nenhuma_fonte:
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
                f"Salvas: {metricas['salvas']} | "
                f"Duplicadas: {metricas['duplicadas']} | "
                f"Erros: {metricas['erros']}"
            )
            logger.info("=" * 60)

        return metricas
