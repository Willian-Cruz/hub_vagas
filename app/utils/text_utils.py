"""Limpeza de texto compartilhada por scrapers, normalizadores e repositório."""
import re
import unicodedata
from typing import Optional

# Textos que os portais usam no lugar de "sem informação". Comparados em
# minúsculas (casefold). Viram None em vez de entrar no banco como dado.
PLACEHOLDERS = frozenset(
    {
        "",
        "-",
        "n/a",
        "não informado",
        "nao informado",
        "não informada",
        "nao informada",
        "localização não informada",
        "localizacao nao informada",
        "confidencial",
    }
)


def normalizar_espacos(texto) -> str:
    """Colapsa qualquer sequência de espaços/quebras de linha em um espaço."""
    if texto is None:
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()


def sem_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def valor_ou_none(texto) -> Optional[str]:
    """Texto limpo, ou None quando vazio ou placeholder do portal."""
    limpo = normalizar_espacos(texto)
    if not limpo or limpo.casefold() in PLACEHOLDERS:
        return None
    return limpo


def chave_conteudo(origem, titulo, empresa, localizacao) -> Optional[str]:
    """Chave para detectar a mesma vaga republicada com outro ID no portal.

    Devolve None se faltar empresa ou local: sem eles, vagas diferentes com o
    mesmo título (ex.: duas "Executivo de Vendas" confidenciais) seriam juntadas.
    """
    if not (origem and titulo and empresa and localizacao):
        return None
    partes = [
        sem_acentos(normalizar_espacos(parte)).casefold()
        for parte in (origem, titulo, empresa, localizacao)
    ]
    return "|".join(partes)
