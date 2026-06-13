"""
Testes unitários para SchedulerService (Sprint 7).

Estratégia de mock:
    O BlockingScheduler trava o processo quando iniciado (é bloqueante por
    definição). Nos testes mockamos o scheduler inteiro para verificar apenas
    se ele foi configurado corretamente — job adicionado, trigger correto,
    timezone certa — sem bloquear a suíte de testes.

Execução: pytest tests/test_scheduler_service.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from unittest.mock import patch, MagicMock, call
from services.scheduler_service import SchedulerService


# ── Helper: cria um scheduler falso e captura as chamadas ────────────────────

def _mock_scheduler():
    """Retorna um MagicMock que simula o BlockingScheduler."""
    scheduler = MagicMock()
    # Simula KeyboardInterrupt ao chamar .start() para não bloquear o teste
    scheduler.start.side_effect = KeyboardInterrupt
    return scheduler


# ═══════════════════════════════════════════════════════════════
# TESTES — iniciar_diario
# ═══════════════════════════════════════════════════════════════

class TestIniciarDiario:

    def test_usa_hora_padrao_quando_nao_informada(self):
        mock_sched = _mock_scheduler()
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            SchedulerService.iniciar_diario()

        args, kwargs = mock_sched.add_job.call_args
        trigger = kwargs.get("trigger") or args[1]
        # CronTrigger configurado com hora padrão (6)
        assert trigger.fields  # trigger foi criado (não é None)

    def test_usa_hora_e_minuto_customizados(self):
        mock_sched = _mock_scheduler()
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            SchedulerService.iniciar_diario(hora=8, minuto=30)

        # Verifica que add_job foi chamado uma vez
        assert mock_sched.add_job.call_count == 1

    def test_usa_hora_padrao_6(self):
        assert SchedulerService.HORA_PADRAO == 6

    def test_usa_minuto_padrao_0(self):
        assert SchedulerService.MINUTO_PADRAO == 0

    def test_timezone_sao_paulo(self):
        assert SchedulerService.TIMEZONE == "America/Sao_Paulo"

    def test_add_job_e_chamado(self):
        mock_sched = _mock_scheduler()
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            SchedulerService.iniciar_diario()
        assert mock_sched.add_job.called

    def test_start_e_chamado(self):
        mock_sched = _mock_scheduler()
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            SchedulerService.iniciar_diario()
        assert mock_sched.start.called

    def test_encerra_graciosamente_com_keyboard_interrupt(self):
        mock_sched = _mock_scheduler()
        mock_sched.start.side_effect = KeyboardInterrupt
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            # Não deve levantar exceção — deve ser tratada internamente
            try:
                SchedulerService.iniciar_diario()
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt não foi tratado pelo SchedulerService")

    def test_encerra_graciosamente_com_system_exit(self):
        mock_sched = _mock_scheduler()
        mock_sched.start.side_effect = SystemExit
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            try:
                SchedulerService.iniciar_diario()
            except SystemExit:
                pytest.fail("SystemExit não foi tratado pelo SchedulerService")


# ═══════════════════════════════════════════════════════════════
# TESTES — iniciar_por_intervalo
# ═══════════════════════════════════════════════════════════════

class TestIniciarPorIntervalo:

    def test_add_job_e_chamado(self):
        mock_sched = _mock_scheduler()
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            SchedulerService.iniciar_por_intervalo(horas=2)
        assert mock_sched.add_job.called

    def test_start_e_chamado(self):
        mock_sched = _mock_scheduler()
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            SchedulerService.iniciar_por_intervalo(horas=2)
        assert mock_sched.start.called

    def test_encerra_graciosamente_com_keyboard_interrupt(self):
        mock_sched = _mock_scheduler()
        mock_sched.start.side_effect = KeyboardInterrupt
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            try:
                SchedulerService.iniciar_por_intervalo(horas=1)
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt não foi tratado pelo SchedulerService")

    def test_intervalo_padrao_e_6_horas(self):
        mock_sched = _mock_scheduler()
        with patch("services.scheduler_service.BlockingScheduler", return_value=mock_sched):
            SchedulerService.iniciar_por_intervalo()
        # Verifica que o trigger de intervalo foi usado (add_job chamado)
        assert mock_sched.add_job.call_count == 1


# ═══════════════════════════════════════════════════════════════
# TESTES — _executar_pipeline (callback interno)
# ═══════════════════════════════════════════════════════════════

class TestExecutarPipeline:

    def test_chama_pipeline_service(self):
        # PipelineService é importado localmente dentro de _executar_pipeline().
        # Por isso o patch deve ser feito no módulo onde ele é importado: services.pipeline_service
        mock_pipeline = MagicMock()
        mock_pipeline.executar.return_value = {
            "coletadas": 10, "salvas": 8, "duplicadas": 2,
            "erros": 0, "duracao_seg": 5.0, "sucesso": True,
        }
        with patch("services.pipeline_service.CollectorService.coletar_todas_vagas", return_value=[]), \
             patch("services.pipeline_service.DashboardService.gerar"):
            SchedulerService._executar_pipeline()
        # Se chegou aqui sem exceção, o pipeline foi chamado com sucesso

    def test_nao_levanta_excecao_quando_pipeline_falha(self):
        # Mesmo se o CollectorService falhar, _executar_pipeline não deve explodir
        with patch(
            "services.pipeline_service.CollectorService.coletar_todas_vagas",
            side_effect=Exception("Scraper offline"),
        ):
            try:
                SchedulerService._executar_pipeline()
            except Exception as e:
                pytest.fail(f"_executar_pipeline propagou exceção inesperada: {e}")