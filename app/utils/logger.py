"""
Configuração central de logging do hub_vagas.

Por que logging em vez de print()?
    - print() some quando o processo roda em background
    - logging grava em arquivo com timestamp, nível e módulo de origem
    - Permite filtrar por nível: INFO no arquivo, WARNING no terminal
    - Padrão da indústria para pipelines de dados

Uso em qualquer módulo:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Mensagem informativa")
    logger.error("Algo deu errado")
"""
import logging
import os
from logging.handlers import RotatingFileHandler

# Diretório de logs sempre relativo à raiz do projeto
LOG_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado com dois handlers:
        - Console: mostra WARNING e acima (não polui o terminal com DEBUG)
        - Arquivo:  grava INFO e acima com timestamp completo
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

    # ── Formato ──────────────────────────────────────────────────────────
    fmt = logging.Formatter(
        fmt     = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S",
    )

    # ── Handler de arquivo (rotativo) ────────────────────────────────────
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes    = 5 * 1024 * 1024,  # 5 MB por arquivo
        backupCount = 3,                 # mantém pipeline.log.1, .2, .3
        encoding    = "utf-8",
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