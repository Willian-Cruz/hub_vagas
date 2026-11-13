"""Classificação de senioridade em cascata (funções puras, sem I/O).

Precedência, da evidência mais forte para a mais fraca:

  1. nível informado pelo portal             -> origem "portal"
  2. palavra de nível no título              -> origem "titulo"
  3. nível explícito na descrição            -> origem "descricao_nivel"
  4. campo de experiência do portal          -> origem "experiencia_campo"  (ex.: InfoJobs "Entre 3 e 5 anos")
  5. "N anos de experiência" na descrição    -> origem "descricao_anos"

Sem evidência, o resultado é (None, None): o dado fica NULL, nunca um palpite.
Guarde `origem` para auditar o que foi inferido: títulos e campos estruturados são confiáveis; as
origens 3 e 5 leem texto livre e podem errar (a descrição do card é só um resumo de ~150 caracteres).

Os rótulos e a regra do TÍTULO seguem o pipeline (NormalizeService.SENIORIDADE_MAP e a macro dbt
normalize_seniority): mesmas palavras, na mesma ordem. Assim o mesmo título recebe o mesmo nível
vindo de qualquer scraper e em qualquer camada. Quando duas palavras de nível aparecem juntas,
vale a primeira da lista: "Pleno/Sênior" -> Pleno, "Gerente Sênior" -> Sênior. Diferenças
propositais em relação ao pipeline, cobertas por tests/test_seniority_service.py:
  - "PL/SQL", "PL-SQL", "PL SQL" e "PL-300" não são "Pleno" (o pipeline lê "PL" como Pleno);
  - palavras a mais: mid-level, principal, aprendiz, intern, chief, vice-presidente, coord.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from utils.text_utils import normalizar_espacos, sem_acentos

ESTAGIO = "Estágio/Trainee"
JUNIOR = "Júnior"
PLENO = "Pleno"
SENIOR = "Sênior"
ESPECIALISTA = "Especialista"
COORDENADOR = "Coordenador"
LIDERANCA = "Liderança"
DIRETORIA = "Diretoria"

# Faixas de experiência -> nível, pelo MÍNIMO de anos, no intervalo [min, max).
# É inferência fraca (não existe regra universal): ajuste aqui ou transforme em seed do dbt.
FAIXAS_EXPERIENCIA = (
    (0, 3, JUNIOR),
    (3, 5, PLENO),
    (5, None, SENIOR),
)

# Aplicadas em texto sem acento e minúsculo. A ordem importa: o primeiro padrão que casar vence,
# e é a mesma ordem do NormalizeService.SENIORIDADE_MAP.
# "pl" sozinho é Pleno, mas "PL/SQL", "PL-SQL", "PL SQL" e "PL-300" não: são banco de dados e
# certificação, não nível. "Pl/Sr" (faixa Pleno/Sênior) continua valendo como Pleno.
_PADROES_TITULO = (
    (JUNIOR, re.compile(r"\b(?:junior|jr)\b")),
    (PLENO, re.compile(r"\bpleno\b|\bmid[- ]?level\b|\bpl\b(?!\s*[/-]?\s*sql\b|[/-]\s*\d)")),
    (SENIOR, re.compile(r"\b(?:senior|sr)\b")),
    (ESPECIALISTA, re.compile(r"\b(?:especialista|specialist|principal)\b")),
    (COORDENADOR, re.compile(r"\b(?:coordenador(?:a)?|coordenacao|coordinator|coord|supervisor(?:a)?|supervisao)\b")),
    (LIDERANCA, re.compile(r"\b(?:gerente|gerencia|manager|lider|leader|lead)\b")),
    (DIRETORIA, re.compile(r"\b(?:diretor(?:a)?|diretoria|director|head|vp|vice[- ]presidente|chief)\b")),
    (ESTAGIO, re.compile(r"\b(?:estagio|estagios|estagiario|estagiaria|estagiarios|estagiarias|aprendiz|trainee|trainees|intern|interns|internship)\b")),
)

# Os próprios rótulos são aceitos como entrada ("Liderança" não casa com nenhum padrão acima).
_ROTULOS = {
    sem_acentos(rotulo).casefold(): rotulo
    for rotulo in (ESTAGIO, JUNIOR, PLENO, SENIOR, ESPECIALISTA, COORDENADOR, LIDERANCA, DIRETORIA)
}

# Descrição, só padrões fortes: "Nível: Pleno", "Analista de Dados Sênior".
# "pleno domínio de Excel" e "empresa com 20 anos de mercado" não contam.
_NIVEL_EXPLICITO = re.compile(r"\b(?:nivel|senioridade|categoria)\s*[:\-]?\s*(junior|pleno|senior|especialista)\b")
_CARGO_COM_NIVEL = re.compile(
    r"\b(?:analista|engenheir[oa]|desenvolvedor(?:a)?|cientista|consultor(?:a)?|arquiteto|arquiteta|programador(?:a)?|profissional)"
    r"\s+(?:d[eao]s?\s+(?:[a-z0-9]+\s+){1,3}?)?(junior|pleno|senior)\b"
)
_NIVEL_POR_PALAVRA = {"junior": JUNIOR, "pleno": PLENO, "senior": SENIOR, "especialista": ESPECIALISTA}

_ANOS_ANTES = re.compile(
    r"(?:(?:mais de|acima de|minimo(?: de)?|no minimo|pelo menos|ao menos)\s+)?"
    r"(\d{1,2})(?:\s*(?:a|ate|e|-)\s*(\d{1,2}))?\s*\+?\s*anos?\s+de\s+(?:experiencia|vivencia|atuacao)"
)
_ANOS_DEPOIS = re.compile(
    r"experiencia\s+(?:minima\s+)?(?:de\s+|com\s+)?(?:mais de\s+|no minimo\s+)?"
    r"(\d{1,2})(?:\s*(?:a|ate|e|-)\s*(\d{1,2}))?\s*\+?\s*anos?"
)

# Campo estruturado de experiência ("Entre 3 e 5 anos", "Mais de 10 anos", "Sem experiência", ...).
_EXP_SEM = re.compile(r"\bsem experiencia\b")
_EXP_SO_ESTAGIO = re.compile(r"\b(?:so|somente|apenas)\s+estagi")
_EXP_FAIXA = re.compile(r"(\d{1,2})\s*(?:a|e|ate|[-–—])\s*(\d{1,2})\s*anos?")
_EXP_MINIMO = re.compile(r"(?:mais de|acima de|mais que|a partir de|no minimo|minimo(?: de)?)\s*(\d{1,2})\s*anos?|(\d{1,2})\s*\+\s*anos?")
_EXP_MAXIMO = re.compile(r"(?:ate|menos de|no maximo|maximo(?: de)?)\s*(\d{1,2})\s*anos?")
_EXP_SIMPLES = re.compile(r"(\d{1,2})\s*anos?")


@dataclass(frozen=True)
class Senioridade:
    nivel: str | None = None
    origem: str | None = None


def _normalizar(texto: str | None) -> str:
    """Espaços colapsados, sem acentos e em minúsculas, para comparar com as regras."""
    return sem_acentos(normalizar_espacos(texto)).casefold()


def nivel_no_texto(texto: str | None) -> str | None:
    """Nível indicado por palavras de um título (ou de um nível informado pelo portal)."""
    base = _normalizar(texto)
    if not base:
        return None
    if base in _ROTULOS:
        return _ROTULOS[base]
    for nivel, padrao in _PADROES_TITULO:
        if padrao.search(base):
            return nivel
    return None


def parse_experiencia(texto: str | None) -> tuple[int, int | None] | None:
    """Campo de experiência -> (mín, máx) em anos; None se não reconhecer.

    "Entre 3 e 5 anos" -> (3, 5) · "Mais de 10 anos" -> (10, None) · "Até 1 ano" -> (0, 1) ·
    "Sem experiência" -> (0, 0) · "1 a 3 anos" -> (1, 3)
    """
    base = _normalizar(texto)
    if not base:
        return None
    if _EXP_SEM.search(base):
        return (0, 0)
    if m := _EXP_FAIXA.search(base):
        return (int(m.group(1)), int(m.group(2)))
    if m := _EXP_MINIMO.search(base):
        return (int(m.group(1) or m.group(2)), None)
    if m := _EXP_MAXIMO.search(base):
        return (0, int(m.group(1)))
    if m := _EXP_SIMPLES.search(base):
        return (int(m.group(1)), None)
    return None


def nivel_por_experiencia(anos_min: int | None) -> str | None:
    """Nível provável para um mínimo de anos de experiência (veja FAIXAS_EXPERIENCIA)."""
    if anos_min is None:
        return None
    for minimo, maximo, nivel in FAIXAS_EXPERIENCIA:
        if anos_min >= minimo and (maximo is None or anos_min < maximo):
            return nivel
    return None


def nivel_pelo_campo_de_experiencia(texto: str | None) -> str | None:
    """Nível sugerido pelo campo de experiência do portal.

    "Só estágios" é a própria vaga de estágio; os demais textos viram anos (parse_experiencia) e
    depois nível (FAIXAS_EXPERIENCIA).
    """
    if _EXP_SO_ESTAGIO.search(_normalizar(texto)):
        return ESTAGIO
    faixa = parse_experiencia(texto)
    return nivel_por_experiencia(faixa[0]) if faixa else None


def nivel_explicito_na_descricao(descricao: str | None) -> str | None:
    """"Nível: Pleno", "Analista de Dados Sênior" na descrição; None se não houver padrão forte."""
    base = _normalizar(descricao)
    if not base:
        return None
    for padrao in (_NIVEL_EXPLICITO, _CARGO_COM_NIVEL):
        if m := padrao.search(base):
            return _NIVEL_POR_PALAVRA[m.group(1)]
    return None


def anos_na_descricao(descricao: str | None) -> tuple[int, int | None] | None:
    """"3 a 5 anos de experiência", "mínimo de 2 anos de experiência", "5+ anos de experiência"."""
    base = _normalizar(descricao)
    if not base:
        return None
    for padrao in (_ANOS_ANTES, _ANOS_DEPOIS):
        if m := padrao.search(base):
            return (int(m.group(1)), int(m.group(2)) if m.group(2) else None)
    return None


def classificar_senioridade(
    titulo: str | None,
    *,
    nivel_portal: str | None = None,
    experiencia: str | None = None,
    descricao: str | None = None,
) -> Senioridade:
    """Decide a senioridade seguindo a precedência descrita no topo do módulo."""
    if nivel := nivel_no_texto(nivel_portal):
        return Senioridade(nivel, "portal")
    if nivel := nivel_no_texto(titulo):
        return Senioridade(nivel, "titulo")
    if nivel := nivel_explicito_na_descricao(descricao):
        return Senioridade(nivel, "descricao_nivel")
    if nivel := nivel_pelo_campo_de_experiencia(experiencia):
        return Senioridade(nivel, "experiencia_campo")
    if (anos := anos_na_descricao(descricao)) and (nivel := nivel_por_experiencia(anos[0])):
        return Senioridade(nivel, "descricao_anos")
    return Senioridade()
