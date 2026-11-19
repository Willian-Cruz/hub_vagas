"""
Configuração central de logging do hub_vagas.

Por que logging em vez de print()?
    - print() some quando o processo roda em background
    - logging grava em arquivo com timestamp, nível e módulo de origem
    - Permite filtrar por nível: INFO no arquivo, WARNING no terminal
    - Padrão da indústria para pipelines de dados

Uso em qualquer módulo:
    from app.utils.logger import get_logger, log_event
    logger = get_logger(__name__)
    logger.info("Mensagem informativa")
    logger.error("Algo deu errado")

    # Log estruturado com run_id (observabilidade M13):
    log_event(
        logger=logger,
        level="INFO",
        run_id="uuid-da-execucao",
        source="Vagas.com",
        component="scraper",
        stage="coleta",
        event="vagas_coletadas",
        status="sucesso",
        duration_ms=1250,
        records_received=28,
        records_persisted=28,
        records_rejected=0,
    )
"""
import json
import logging
import os
from datetime import UTC
from logging.handlers import RotatingFileHandler

# Diretório de logs sempre relativo à raiz do projeto
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")


class JSONFormatter(logging.Formatter):
    """Formata registros de log como JSON em uma linha."""

    def format(self, record: logging.LogRecord) -> str:
        entrada = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "component": getattr(record, "component", record.name),
            "mensagem": record.getMessage(),
        }
        # Campos extras passados via log_event ou extra=
        for chave in (
            "run_id", "source", "stage", "event", "status",
            "duration_ms", "records_received", "records_persisted",
            "records_duplicated", "records_rejected", "error_type", "error_message",
        ):
            valor = getattr(record, chave, None)
            if valor is not None:
                entrada[chave] = valor
        if record.exc_info:
            entrada["error_type"] = record.exc_info[0].__name__
            entrada["error_message"] = str(record.exc_info[1])
        return json.dumps(entrada, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado com dois handlers:
        - Console: mostra INFO e acima
        - Arquivo: grava INFO e acima em JSON (uma linha por evento)
                   Rotaciona em 5 MB, mantém 3 arquivos de backup

    Args:
        name: normalmente __name__ do módulo que chama

    Returns:
        Logger configurado e pronto para uso
    """
    logger = logging.getLogger(name)

    # Evita adicionar handlers duplicados se get_logger for chamado várias vezes
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ── Formato JSON ───────────────────────────────────────────────────────
    fmt = JSONFormatter()

    # ── Handler de arquivo (rotativo) ────────────────────────────────────
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB por arquivo
        backupCount=3,  # mantém pipeline.log.1, .2, .3
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)

    # ── Handler de console ───────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_event(
    logger: logging.Logger,
    level: str = "INFO",
    run_id: str | None = None,
    source: str | None = None,
    component: str | None = None,
    stage: str | None = None,
    event: str | None = None,
    status: str | None = None,
    duration_ms: float | None = None,
    records_received: int | None = None,
    records_persisted: int | None = None,
    records_duplicated: int | None = None,
    records_rejected: int | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
    mensagem: str | None = None,
) -> None:
    """
    Emite um log estruturado (JSON em uma linha) para observabilidade.

    Todos os campos são opcionais; preencha apenas os relevantes para o evento.
    O campo `mensagem` permite texto livre adicional.

    Exemplo de saída:
        {"timestamp":"2026-11-18T02:00:00Z","level":"INFO","run_id":"...",
         "source":"Vagas.com","component":"scraper","stage":"coleta",
         "event":"vagas_coletadas","status":"sucesso","duration_ms":1250,
         "records_received":28,"records_persisted":28,"records_rejected":0}
    """
    from datetime import datetime

    entrada = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level,
    }
    if run_id is not None:
        entrada["run_id"] = run_id
    if source is not None:
        entrada["source"] = source
    if component is not None:
        entrada["component"] = component
    if stage is not None:
        entrada["stage"] = stage
    if event is not None:
        entrada["event"] = event
    if status is not None:
        entrada["status"] = status
    if duration_ms is not None:
        entrada["duration_ms"] = duration_ms
    if records_received is not None:
        entrada["records_received"] = records_received
    if records_persisted is not None:
        entrada["records_persisted"] = records_persisted
    if records_duplicated is not None:
        entrada["records_duplicated"] = records_duplicated
    if records_rejected is not None:
        entrada["records_rejected"] = records_rejected
    if error_type is not None:
        entrada["error_type"] = error_type
    if error_message is not None:
        entrada["error_message"] = error_message

    # Mensagem de texto livre (vai para record.getMessage, não duplicada em JSON)
    mensagem_log = mensagem or ""

    # Campos extras estruturados (timestamp e level já estão em entrada)
    campos_extra = {k: v for k, v in entrada.items() if k not in ("timestamp", "level")}

    nivel = getattr(logging, level.upper(), logging.INFO)
    logger.log(nivel, mensagem_log, extra=campos_extra)
