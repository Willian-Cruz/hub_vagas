"""Parser da listagem de vagas da Catho (HTML real capturado em 11/11/2026).

Cada vaga é um <li data-offer-item="ID"> com:

  span.tag              "Publicada|Atualizada" + "Hoje" | "Ontem" | "em dd/mm" (sem ano).
                        A classe CSS (pub_hoje / pub_ontem) NÃO é confiável: "Publicada em 26/10"
                        também vem com pub_ontem. Vale o texto.
  h2.title_offer a      título e href (/vagas/<slug>/<id>)
  article > p           empresa: primeiro <span>. Anônima = "Empresa Confidencial" + <button>Por que?</button>
                        (por isso não se usa o texto do <p> inteiro)
  p com .i_job_location "<strong>N vaga(s)</strong> - Cidade"  (sem UF; N é a quantidade de posições)
  p com .i_salary       "R$ 3.675 + 2 benefícios" | "A Combinar" | "A partir de R$ 3.000,00" | "Até R$ 2.000,00"

O card NÃO traz descrição, experiência, escolaridade nem modalidade: isso só existe no detalhe
da vaga. Por isso a senioridade aqui vem só do título.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

from scrapers.parser_utils import (
    CardParseado,
    empresa_ou_none,
    limpar,
    parse_salario,
    salario_sem_beneficios,
)
from services.seniority_service import classificar_senioridade

SOURCE = "Catho"
BASE_URL = "https://www.catho.com.br"
FUSO = ZoneInfo("America/Sao_Paulo")

_VAGAS_E_LOCAL = re.compile(r"^(\d+)\s+vagas?\s*-\s*(.+)$", re.IGNORECASE)
_PREFIXO_VAGAS = re.compile(r"^\d+\s+vagas?\s*-?\s*", re.IGNORECASE)
_DATA_CARD = re.compile(
    r"^(publicada|atualizada)\s+(?:(hoje|ontem)|em\s+(\d{1,2})/(\d{1,2}))$", re.IGNORECASE
)


def parse_data_card(texto: str | None, hoje: date) -> tuple[str | None, date | None]:
    """"Publicada Ontem" -> ("publicada", hoje-1). Sem ano no texto, vale o ano mais recente que não seja futuro.

    Devolve (None, None) quando o texto não é uma data reconhecível.
    """
    texto = limpar(texto)
    m = _DATA_CARD.match(texto) if texto else None
    if m is None:
        return None, None
    tipo = m.group(1).lower()
    if m.group(2):
        recuo = 0 if m.group(2).lower() == "hoje" else 1
        return tipo, hoje - timedelta(days=recuo)
    dia, mes = int(m.group(3)), int(m.group(4))
    for ano in (hoje.year, hoje.year - 1):
        try:
            candidata = date(ano, mes, dia)
        except ValueError:
            continue
        if candidata <= hoje:
            return tipo, candidata
    return None, None


def _paragrafo_do_icone(li: Tag, seletor_icone: str) -> Tag | None:
    icone = li.select_one(seletor_icone)
    return icone.find_parent("p") if icone else None


def _parse_card(li: Tag, hoje: date) -> CardParseado | None:
    id_externo = limpar(li.get("data-offer-item"))
    ancora = li.select_one("h2.title_offer a")
    if not id_externo or ancora is None:
        return None
    titulo = limpar(ancora.get_text()) or limpar(ancora.get("title"))
    href = ancora.get("href")
    if not titulo or not href:
        return None

    # Empresa: 1º <p> do article sem ícone; só o <span>, sem o botão "Por que?".
    empresa = None
    for p in li.select("article > p"):
        if p.select_one(".icon"):
            continue
        span = p.find("span")
        empresa = empresa_ou_none((span or p).get_text())
        break

    # Local: "5 vagas - Piracicaba" -> qtd_posicoes=5, localizacao="Piracicaba".
    qtd_posicoes, localizacao = None, None
    p_local = _paragrafo_do_icone(li, ".i_job_location")
    if p_local is not None:
        texto_local = limpar(p_local.get_text()) or ""
        m = _VAGAS_E_LOCAL.match(texto_local)
        if m:
            qtd_posicoes, localizacao = int(m.group(1)), limpar(m.group(2))
        else:
            localizacao = limpar(_PREFIXO_VAGAS.sub("", texto_local))

    # Salário: texto sem o sufixo "+ N benefícios"; benefícios e faixa ficam em `extra`.
    p_salario = _paragrafo_do_icone(li, ".i_salary")
    salario_bruto = limpar(p_salario.get_text()) if p_salario is not None else None
    estruturado = parse_salario(salario_bruto)

    # Data: o texto manda. "Atualizada" não é data de publicação.
    tipo_data, data_card = None, None
    for tag in li.select("span.tag"):
        tipo_data, data_card = parse_data_card(tag.get_text(), hoje)
        if tipo_data:
            break
    data_dia = datetime.combine(data_card, time.min) if data_card else None

    senioridade = classificar_senioridade(titulo)

    job = {
        "titulo": titulo,
        "link": urljoin(BASE_URL, href),
        "origem": SOURCE,
        "empresa": empresa,
        "senioridade": senioridade.nivel,
        "localizacao": localizacao,
        "descricao": None,
        "salario": salario_sem_beneficios(salario_bruto),
        "id_externo": id_externo,
        "data_publicacao": data_dia if tipo_data == "publicada" else None,
        "modalidade": None,
        "experiencia": None,
        "escolaridade": None,
        "qtd_posicoes": qtd_posicoes,
        "raw_payload": {"html_fragment": str(li)},
    }
    extra = {
        "data_atualizacao": data_dia if tipo_data == "atualizada" else None,
        "salario_tipo": estruturado["tipo"],
        "salario_min": estruturado["min"],
        "salario_max": estruturado["max"],
        "beneficios_qtd": estruturado["beneficios_qtd"],
        "senioridade_origem": senioridade.origem,
    }
    return CardParseado(job=job, extra=extra)


def parse_cards(html: str, hoje: date | None = None) -> list[CardParseado]:
    """Lê todos os cards da página. `hoje` (padrão: hoje em America/Sao_Paulo) resolve "Hoje/Ontem/dd-mm"."""
    hoje = hoje or datetime.now(FUSO).date()
    soup = BeautifulSoup(html, "html.parser")
    vistos: set[str] = set()
    cards: list[CardParseado] = []
    for li in soup.select("li[data-offer-item]"):
        card = _parse_card(li, hoje)
        if card is None or card.job["id_externo"] in vistos:
            continue
        vistos.add(card.job["id_externo"])
        cards.append(card)
    return cards
