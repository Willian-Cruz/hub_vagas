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
                "coletadas":   int,   # vagas retornadas pelos scrapers
                "salvas":      int,   # vagas efetivamente inseridas no banco
                "duplicadas":  int,   # vagas ignoradas por já existirem
                "erros":       int,   # vagas que falharam ao salvar
                "fontes":      list,  # status, contagem e erro por scraper
                "duracao_seg": float, # tempo total em segundos
                "sucesso":     bool,  # False se coleta, persistência ou dashboard falhar
            }
        """
        logger.info("=" * 60)
        logger.info("PIPELINE INICIADO")
        logger.info("=" * 60)

        metricas = {
            "coletadas":   0,
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
                }
                for resultado in resultados
            ]
            vagas = [vaga for resultado in resultados for vaga in resultado.jobs]
            metricas["coletadas"] = len(vagas)
            logger.info(f"Coletadas: {len(vagas)} vagas")

            fontes_com_falha = [
                resultado
                for resultado in resultados
                if resultado.status not in (ScrapeStatus.SUCCESS, ScrapeStatus.EMPTY)
            ]
            for resultado in resultados:
                logger.info(
                    f"Fonte {resultado.source}: {resultado.status.value} | "
                    f"Vagas: {len(resultado.jobs)} | "
                    f"Páginas: {resultado.pages_processed}"
                )
                if resultado.error:
                    logger.warning(f"Fonte {resultado.source}: {resultado.error}")

            # Zero vagas quase sempre indica scraper quebrado ou portal bloqueando.
            # Falhar aqui evita um "sucesso" silencioso que esconde o problema.
            if not vagas:
                raise RuntimeError(
                    "Nenhuma vaga coletada: verifique os scrapers e o acesso aos portais"
                )

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

            # ── 3. Dashboard ───────────────────────────────────────────
            logger.info("Etapa 3/3: Regenerando dashboard...")
            DashboardService.gerar()
            logger.info("Dashboard atualizado com sucesso")

            metricas["sucesso"] = metricas["erros"] == 0 and not fontes_com_falha

            if metricas["erros"] or fontes_com_falha:
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
                f"Salvas: {metricas['salvas']} | "
                f"Duplicadas: {metricas['duplicadas']} | "
                f"Erros: {metricas['erros']}"
            )
            logger.info("=" * 60)

        return metricas
