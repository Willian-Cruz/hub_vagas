"""Utilitários compartilhados pelos parsers de HTML dos portais (funções puras, sem I/O)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_ESPACOS = re.compile(r"\s+")
_CONFIDENCIAL = re.compile(r"^(?:empresa\s+)?confidencial$", re.IGNORECASE)
_BENEFICIOS = re.compile(r"\s*\+\s*(\d+)\s*benef[ií]cios?\s*$", re.IGNORECASE)
_VALOR = re.compile(r"R\$\s*(\d+(?:\.\d{3})*(?:,\d{1,2})?)")


@dataclass(frozen=True)
class CardParseado:
    """Resultado do parse de um card.

    job:   chaves = campos do JobSchema (campo ausente = None), prontas para JobSchema(**job).
    extra: dados auxiliares que ainda não existem no JobSchema (salário estruturado,
           faixa de experiência em anos, origem da senioridade etc.).
    """

    job: dict
    extra: dict = field(default_factory=dict)


def limpar(texto: str | None) -> str | None:
    """Colapsa espaços e quebras de linha. Texto vazio vira None."""
    if texto is None:
        return None
    texto = _ESPACOS.sub(" ", texto).strip()
    return texto or None


def sem_acentos(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar com regras."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


def empresa_ou_none(texto: str | None) -> str | None:
    """Nome da empresa; None para vazio ou "Empresa confidencial"."""
    texto = limpar(texto)
    if texto is None or _CONFIDENCIAL.match(texto):
        return None
    return texto


def _para_float(valor: str) -> float:
    return float(valor.replace(".", "").replace(",", "."))


def salario_sem_beneficios(texto: str | None) -> str | None:
    """'R$ 3.675 + 2 benefícios' -> 'R$ 3.675'; 'A Combinar + 3 benefícios' -> 'A Combinar'."""
    texto = limpar(texto)
    if texto is None:
        return None
    return limpar(_BENEFICIOS.sub("", texto))


def parse_salario(texto: str | None) -> dict:
    """Interpreta o texto de salário dos portais.

    Retorna {"tipo", "min", "max", "beneficios_qtd"}, com tipo em
    "faixa" | "fixo" | "a_partir" | "ate" | "a_combinar" | None.

    Exemplos: "R$ 4.000,00 a R$ 4.900,00" -> faixa 4000-4900; "Até R$ 2.000,00" -> ate (max 2000);
    "A partir de R$ 3.000,00" -> a_partir (min 3000); "R$ 3.675 + 2 benefícios" -> fixo 3675, 2 benefícios.
    """
    resultado = {"tipo": None, "min": None, "max": None, "beneficios_qtd": None}
    texto = limpar(texto)
    if texto is None:
        return resultado
    beneficios = _BENEFICIOS.search(texto)
    if beneficios:
        resultado["beneficios_qtd"] = int(beneficios.group(1))
        texto = texto[: beneficios.start()]
    valores = [_para_float(v) for v in _VALOR.findall(texto)]
    base = sem_acentos(texto)
    if not valores:
        if "combinar" in base:
            resultado["tipo"] = "a_combinar"
        return resultado
    if len(valores) >= 2:
        resultado.update(tipo="faixa", min=min(valores), max=max(valores))
    elif base.startswith("a partir"):
        resultado.update(tipo="a_partir", min=valores[0])
    elif base.startswith("ate"):
        resultado.update(tipo="ate", max=valores[0])
    else:
        resultado.update(tipo="fixo", min=valores[0], max=valores[0])
    return resultado
