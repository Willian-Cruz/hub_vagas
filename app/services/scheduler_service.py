"""
SchedulerService — gerencia o agendamento do pipeline.

Por que APScheduler?
    - Roda dentro do processo Python, sem infraestrutura externa
    - Não precisa configurar cron do SO, Celery ou Redis
    - Suporta fusos horários, intervalos, datas específicas e cron expressions
    - Ideal para portfólio: simples de entender e demonstrar

Modos disponíveis:
    - Diário:    executa todo dia às 06:00 (padrão)
    - Intervalo: executa a cada N horas (útil para debug)
    - Único:     executa uma vez imediatamente e encerra (útil para teste)
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from utils.logger import get_logger

logger = get_logger(__name__)


class SchedulerService:

    # Horário padrão de execução diária (formato HH:MM, fuso de São Paulo)
    HORA_PADRAO   = 6
    MINUTO_PADRAO = 0
    TIMEZONE      = "America/Sao_Paulo"

    @classmethod
    def iniciar_diario(cls, hora: int = None, minuto: int = None) -> None:
        """
        Inicia o agendador em modo diário.
        Mantém o processo vivo e executa o pipeline todo dia no horário definido.

        Args:
            hora:   hora da execução (0-23). Padrão: 6
            minuto: minuto da execução (0-59). Padrão: 0
        """
        hora   = hora   if hora   is not None else cls.HORA_PADRAO
        minuto = minuto if minuto is not None else cls.MINUTO_PADRAO

        scheduler = BlockingScheduler(timezone=cls.TIMEZONE)

        scheduler.add_job(
            func    = cls._executar_pipeline,
            trigger = CronTrigger(hour=hora, minute=minuto, timezone=cls.TIMEZONE),
            id      = "pipeline_diario",
            name    = "Pipeline Hub Vagas",
            replace_existing = True,
        )

        logger.info(f"Agendador iniciado — execução diária às {hora:02d}:{minuto:02d} ({cls.TIMEZONE})")
        logger.info("Pressione Ctrl+C para encerrar")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Agendador encerrado pelo usuário")

    @classmethod
    def iniciar_por_intervalo(cls, horas: int = 6) -> None:
        """
        Inicia o agendador em modo intervalo.
        Útil para debug — executa a cada N horas.

        Args:
            horas: intervalo em horas entre cada execução. Padrão: 6
        """
        scheduler = BlockingScheduler(timezone=cls.TIMEZONE)

        scheduler.add_job(
            func    = cls._executar_pipeline,
            trigger = IntervalTrigger(hours=horas),
            id      = "pipeline_intervalo",
            name    = f"Pipeline a cada {horas}h",
            replace_existing = True,
        )

        logger.info(f"Agendador iniciado — execução a cada {horas}h")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Agendador encerrado pelo usuário")

    @staticmethod
    def _executar_pipeline() -> None:
        """
        Callback chamado pelo agendador.
        Importação local evita importação circular na inicialização.
        """
        # Importação local intencional: evita que o banco seja conectado
        # antes da configuração do agendador estar completa
        from services.pipeline_service import PipelineService

        logger.info("Agendador disparou a execução do pipeline")
        metricas = PipelineService.executar()

        if not metricas["sucesso"]:
            logger.error("Pipeline encerrou com falha — verifique os logs")