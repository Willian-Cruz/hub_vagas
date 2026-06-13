"""
PipelineService — orquestra uma execução completa do pipeline.

Responsabilidades:
    1. Coleta vagas via CollectorService (todos os scrapers)
    2. Persiste cada vaga via JobRepository (com normalização)
    3. Regenera o dashboard HTML atualizado
    4. Registra início, fim, duração e erros no log

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
from services.dashboard_service import DashboardService

logger = get_logger(__name__)


class PipelineService:

    @staticmethod
    def executar() -> dict:
        """
        Executa o pipeline completo de coleta, persistência e dashboard.

        Returns:
            dict com métricas da execução:
            {
                "coletadas":   int,   # vagas retornadas pelos scrapers
                "salvas":      int,   # vagas efetivamente inseridas no banco
                "duplicadas":  int,   # vagas ignoradas por já existirem
                "erros":       int,   # vagas que falharam ao salvar
                "duracao_seg": float, # tempo total em segundos
                "sucesso":     bool,  # False se houve exceção geral
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
            "duracao_seg": 0.0,
            "sucesso":     False,
        }

        inicio = time.time()

        try:
            # ── 1. Coleta ──────────────────────────────────────────────
            logger.info("Etapa 1/3: Coletando vagas...")
            vagas = CollectorService.coletar_todas_vagas()
            metricas["coletadas"] = len(vagas)
            logger.info(f"Coletadas: {len(vagas)} vagas")

            # ── 2. Persistência ────────────────────────────────────────
            logger.info("Etapa 2/3: Persistindo no banco...")

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

            metricas["sucesso"] = True

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