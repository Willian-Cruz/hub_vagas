"""Notificação de falha do pipeline (webhook Discord/Telegram ou e-mail simples).

Variáveis de ambiente opcionais:
    NOTIFICACAO_WEBHOOK_URL — URL do webhook (Discord ou Telegram)
    NOTIFICACAO_EMAIL_TO    — destino de e-mail (se SMTP configurado)
    NOTIFICACAO_EMAIL_FROM  — remetente
    SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS — servidor SMTP

Se nenhuma estiver configurada, a notificação é apenas logada (não falha o pipeline).
"""
from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from utils.logger import get_logger

logger = get_logger(__name__)


def enviar_falha(metricas: dict, erro: str | None = None) -> None:
    """Envia notificação de falha (ou loga se não houver canal configurado)."""
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
                    logger.info("Notificação de falha enviada via webhook")
                    return
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
            logger.info("Notificação de falha enviada por e-mail")
            return
        except Exception as exc:
            logger.warning("Falha ao enviar e-mail: %s", exc)

    # 3. Fallback: apenas log
    logger.error("Falha no pipeline (sem canal de notificação configurado): %s", corpo)
