"""Notificação de falha do pipeline e alertas operacionais (M13/M14).

Variáveis de ambiente opcionais:
    NOTIFICACAO_WEBHOOK_URL — URL do webhook (Discord ou Telegram)
    NOTIFICACAO_EMAIL_TO    — destino de e-mail (se SMTP configurado)
    NOTIFICACAO_EMAIL_FROM  — remetente
    SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS — servidor SMTP

Se nenhuma estiver configurada, a notificação é apenas logada (não falha o pipeline).

Alertas implementados (conforme docs/operations/observabilidade.md):
    1. Fonte sem execução no período esperado (>72h sem SUCCESS)
    2. Falhas consecutivas (3 execuções seguidas com status=FAILED)
    3. Queda de volume >50% frente à média semanal
    4. Aumento de rejeições (desvio de qualidade >10pp vs mediana 7d)
    5. Falha crítica de persistência (raw erros > 0 em execução)
    6. Falha em modelos dbt (dbt build com ERROR)
    7. Dados desatualizados (último SUCCESS >72h)
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.utils.logger import get_logger, log_event

logger = get_logger(__name__)


def _enviar_notificacao(assunto: str, corpo: str, nivel: str = "WARNING") -> bool:
    """Envia notificação via webhook ou e-mail. Retorna True se enviado com sucesso."""
    # 1. Webhook (Discord / Telegram)
    webhook_url = os.getenv("NOTIFICACAO_WEBHOOK_URL")
    if webhook_url:
        try:
            payload = json.dumps({"content": assunto + "\n" + corpo}).encode("utf-8")
            req = Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    logger.warning("Webhook retornou HTTP %s", resp.status)
                else:
                    logger.info("Notificação enviada via webhook: %s", assunto)
                    return True
        except (URLError, HTTPError, OSError) as exc:
            logger.warning("Falha ao enviar webhook: %s", exc)

    # 2. E-mail (SMTP)
    smtp_host = os.getenv("SMTP_HOST")
    if smtp_host:
        try:
            msg = EmailMessage()
            msg["Subject"] = assunto
            msg["From"] = os.getenv("NOTIFICACAO_EMAIL_FROM", "hub-vagas@localhost")
            msg["To"] = os.getenv("NOTIFICACAO_EMAIL_TO", "dev@localhost")
            msg.set_content(corpo)
            porta = int(os.getenv("SMTP_PORT", "25"))
            with smtplib.SMTP(smtp_host, porta, timeout=10) as smtp:
                usuario = os.getenv("SMTP_USER")
                senha = os.getenv("SMTP_PASS")
                if usuario and senha:
                    smtp.starttls()
                    smtp.login(usuario, senha)
                smtp.send_message(msg)
            logger.info("Notificação enviada por e-mail: %s", assunto)
            return True
        except Exception as exc:
            logger.warning("Falha ao enviar e-mail: %s", exc)

    # 3. Fallback: apenas log
    logger.log(getattr(logging, nivel.upper(), logging.WARNING), "Alerta (sem canal configurado): %s - %s", assunto, corpo)
    return False


def enviar_falha(metricas: dict, erro: str | None = None) -> None:
    """Envia notificação de falha completa do pipeline (ou loga se não houver canal)."""
    run_id = metricas.get("run_id", "desconhecido")
    duracao = metricas.get("duracao_seg", 0)
    fontes_falha = metricas.get("fontes_falha", 0)
    coletadas = metricas.get("coletadas", 0)

    assunto = f"[hub_vagas] Pipeline falhou — run {str(run_id)[:8]}"
    corpo = (
        f"Pipeline de ingestão falhou.\n"
        f"Run ID: {run_id}\n"
        f"Duração: {duracao}s\n"
        f"Vagas coletadas: {coletadas}\n"
        f"Fontes em falha: {fontes_falha}\n"
        f"Erro: {erro or 'sem detalhe'}\n"
    )

    _enviar_notificacao(assunto, corpo, "ERROR")


def alertar_fonte_sem_execucao(origem: str, ultima_sucesso: str | None, horas_sem_sucesso: float) -> None:
    """Alerta 1: Fonte sem execução no período esperado (>72h sem SUCCESS)."""
    assunto = f"[hub_vagas] Alerta: Fonte {origem} sem coleta bem-sucedida há {horas_sem_sucesso:.0f}h"
    corpo = (
        f"Fonte: {origem}\n"
        f"Última coleta SUCCESS: {ultima_sucesso or 'nunca'}\n"
        f"Horas sem SUCCESS: {horas_sem_sucesso:.1f}\n"
        f"Limiar: 72h\n"
        f"Ação: Verificar scraper da fonte\n"
    )
    log_event(
        logger=logger,
        level="WARNING",
        component="alert",
        stage="monitoramento",
        event="fonte_sem_execucao",
        status="alerta",
        source=origem,
        mensagem=f"Fonte {origem} sem SUCCESS há {horas_sem_sucesso:.0f}h",
    )
    _enviar_notificacao(assunto, corpo, "WARNING")


def alertar_falhas_consecutivas(origem: str, contagem_falhas: int, ultimas_execucoes: list[dict]) -> None:
    """Alerta 2: Falhas consecutivas (3 execuções seguidas com status=FAILED)."""
    assunto = f"[hub_vagas] Alerta: {contagem_falhas} falhas consecutivas na fonte {origem}"
    linhas = [f"Fonte: {origem}", f"Falhas consecutivas: {contagem_falhas}", "Últimas execuções:"]
    for ex in ultimas_execucoes:
        linhas.append(f"  - {ex.get('started_at')}: {ex.get('status')} ({ex.get('error', 'sem erro')})")
    linhas.append("Ação: Investigar scraper/banco")
    corpo = "\n".join(linhas)
    log_event(
        logger=logger,
        level="ERROR",
        component="alert",
        stage="monitoramento",
        event="falhas_consecutivas",
        status="alerta",
        source=origem,
        mensagem=f"{contagem_falhas} falhas consecutivas em {origem}",
    )
    _enviar_notificacao(assunto, corpo, "ERROR")


def alertar_queda_volume(origem: str, volume_atual: int, media_semanal: float, pct_queda: float) -> None:
    """Alerta 3: Queda de volume >50% frente à média semanal."""
    assunto = f"[hub_vagas] Alerta: Queda de volume {pct_queda:.0f}% na fonte {origem}"
    corpo = (
        f"Fonte: {origem}\n"
        f"Volume atual: {volume_atual}\n"
        f"Média semanal: {media_semanal:.1f}\n"
        f"Queda: {pct_queda:.1f}%\n"
        f"Limiar: 50%\n"
        f"Ação: Verificar portal/filtro de relevância\n"
    )
    log_event(
        logger=logger,
        level="ERROR",
        component="alert",
        stage="monitoramento",
        event="queda_volume",
        status="alerta",
        source=origem,
        records_received=volume_atual,
        mensagem=f"Queda de volume {pct_queda:.0f}% em {origem}",
    )
    _enviar_notificacao(assunto, corpo, "ERROR")


def alertar_desvio_qualidade(origem: str, campo: str, pct_atual: float, mediana_7d: float, desvio_pp: float) -> None:
    """Alerta 4: Aumento de rejeições (desvio de qualidade >10pp vs mediana 7d)."""
    assunto = f"[hub_vagas] Alerta: Desvio de qualidade {desvio_pp:.1f}pp em {campo} ({origem})"
    corpo = (
        f"Fonte: {origem}\n"
        f"Campo: {campo}\n"
        f"% não-nulo atual: {pct_atual:.1f}%\n"
        f"Mediana 7d: {mediana_7d:.1f}%\n"
        f"Desvio: {desvio_pp:.1f}pp\n"
        f"Limiar: 10pp\n"
        f"Ação: Recalibrar parser\n"
    )
    log_event(
        logger=logger,
        level="WARNING",
        component="alert",
        stage="monitoramento",
        event="desvio_qualidade",
        status="alerta",
        source=origem,
        mensagem=f"Desvio qualidade {desvio_pp:.1f}pp em {campo} ({origem})",
    )
    _enviar_notificacao(assunto, corpo, "WARNING")


def alertar_persistencia_raw_erros(metricas: dict) -> None:
    """Alerta 5: Falha crítica de persistência (raw erros > 0 em execução)."""
    erros = metricas.get("records_rejected", 0)
    if erros == 0:
        return
    run_id = metricas.get("run_id", "desconhecido")
    assunto = f"[hub_vagas] Alerta: Erros de persistência na raw ({erros} registros)"
    corpo = (
        f"Run ID: {run_id}\n"
        f"Registros rejeitados: {erros}\n"
        f"Registros inseridos: {metricas.get('records_inserted', 0)}\n"
        f"Registros atualizados: {metricas.get('records_updated', 0)}\n"
        f"Ação: Verificar banco/conexão\n"
    )
    log_event(
        logger=logger,
        level="ERROR",
        component="alert",
        stage="persistencia",
        event="raw_erros",
        status="alerta",
        run_id=str(run_id) if run_id else None,
        records_rejected=erros,
        mensagem=f"Erros de persistência: {erros} registros rejeitados",
    )
    _enviar_notificacao(assunto, corpo, "ERROR")


def alertar_dbt_falha(run_id: str, subcomando: str, codigo_retorno: int, duracao: float) -> None:
    """Alerta 6: Falha em modelos dbt (dbt build com ERROR)."""
    assunto = f"[hub_vagas] Alerta: dbt {subcomando} falhou (código {codigo_retorno})"
    corpo = (
        f"Run ID: {run_id}\n"
        f"Subcomando: dbt {subcomando}\n"
        f"Código de retorno: {codigo_retorno}\n"
        f"Duração: {duracao}s\n"
        f"Ação: Verificar modelos SQL\n"
    )
    log_event(
        logger=logger,
        level="ERROR",
        component="alert",
        stage="transformacao",
        event="dbt_falha",
        status="alerta",
        run_id=run_id,
        mensagem=f"dbt {subcomando} falhou com código {codigo_retorno}",
    )
    _enviar_notificacao(assunto, corpo, "ERROR")


def alertar_dados_desatualizados(origem: str, ultima_sucesso: str, horas_desatualizado: float) -> None:
    """Alerta 7: Dados desatualizados (último SUCCESS >72h)."""
    assunto = f"[hub_vagas] Alerta: Dados desatualizados na fonte {origem} ({horas_desatualizado:.0f}h)"
    corpo = (
        f"Fonte: {origem}\n"
        f"Última coleta SUCCESS: {ultima_sucesso}\n"
        f"Horas desatualizado: {horas_desatualizado:.1f}\n"
        f"Limiar: 72h\n"
        f"Ação: Verificar agendamento\n"
    )
    log_event(
        logger=logger,
        level="WARNING",
        component="alert",
        stage="monitoramento",
        event="dados_desatualizados",
        status="alerta",
        source=origem,
        mensagem=f"Dados desatualizados em {origem} ({horas_desatualizado:.0f}h)",
    )
    _enviar_notificacao(assunto, corpo, "WARNING")