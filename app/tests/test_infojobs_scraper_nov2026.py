"""InfoJobsScraper contra HTML real (20 vagas capturadas em 11/11/2026) e cards sintéticos.

Os valores esperados foram conferidos à mão no HTML. Se o portal mudar o layout, salve cards
novos em tests/fixtures/ e ajuste os valores daqui.

Três erros que estes testes impedem de voltar:
  - modalidade vazia: o portal tem um ícone para cada valor (Presencial, Híbrido, Home office);
  - Bronze com o HTML mexido: ler o local apagava do card a distância e as coordenadas da vaga;
  - senioridade sempre vazia: agora vem da cascata título > descrição > campo de experiência.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from constants.selectors import INFOJOBS_JOB_CARD
from scrapers.infojobs_scraper import InfoJobsScraper
from services.normalize_service import NormalizeService
from utils.text_utils import normalizar_espacos

FIXTURES = Path(__file__).parent / "fixtures"

# id da vaga -> (senioridade, origem), vaga a vaga, conferido contra título e experiência do HTML.
SENIORIDADE_ESPERADA = {
    "12149951": (None, None),
    "12211273": ("Pleno", "titulo"),
    "12210993": ("Pleno", "experiencia_campo"),     # sem nível no título; experiência 3–5 anos
    "12210955": ("Júnior", "titulo"),
    "12210878": (None, None),
    "12210851": ("Pleno", "experiencia_campo"),
    "12210794": ("Pleno", "experiencia_campo"),
    "12210649": ("Sênior", "titulo"),                # título Sênior, experiência 3–5 anos: o título vence
    "12210645": (None, None),
    "12210583": ("Júnior", "titulo"),
    "12210483": ("Júnior", "experiencia_campo"),    # experiência 1–3 anos
    "12210371": (None, None),
    "12210341": ("Júnior", "experiencia_campo"),
    "12210188": (None, None),
    "12209880": ("Sênior", "titulo"),
    "12209567": ("Júnior", "titulo"),
    "12209530": ("Júnior", "titulo"),
    "12209153": ("Pleno", "titulo"),                 # título Pleno, experiência 5–10 anos: o título vence
    "12209012": ("Pleno", "titulo"),                 # a descrição cita PL/SQL: não interfere
    "12208680": (None, None),
}


@pytest.fixture(scope="module")
def html() -> bytes:
    return (FIXTURES / "infojobs_cards_2026_11.html").read_bytes()


@pytest.fixture(scope="module")
def resultado(html):
    return InfoJobsScraper._parsear_detalhado(html)


@pytest.fixture(scope="module")
def vagas(resultado) -> dict:
    return {vaga.id_externo: vaga for vaga in resultado[0]}


# ---------------------------------------------------------------- página real


def test_le_as_20_vagas_sem_duplicar(resultado, vagas, html):
    jobs, invalidos, total = resultado
    assert (len(jobs), invalidos, total) == (20, 0, 20)
    assert len(vagas) == 20
    # armadilha do portal: ".js_rowCard" casa o card externo E o bloco interno (40 para 20 vagas)
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select(".js_rowCard")) == 2 * len(vagas)


def test_empresa_com_os_dois_formatos_de_link(vagas):
    assert vagas["12149951"].empresa == "RH PRO - Gestão Estratégica e Desenvolvimento Humano"  # /empresa-...aspx
    assert vagas["12211273"].empresa == "Ânima Educação"                                       # /anima-educacao
    assert vagas["12210955"].empresa == "Randstad - Matriz"                                    # /randstad-recursos-humanos
    assert vagas["12209153"].empresa is None                                                   # "Empresa confidencial"
    assert sum(v.empresa is None for v in vagas.values()) == 1


def test_localizacao_sem_a_distancia_oculta(vagas):
    assert vagas["12149951"].localizacao == "São Paulo - SP"
    assert vagas["12211273"].localizacao == "Todo Brasil"
    assert all("Km" not in (v.localizacao or "") for v in vagas.values())


def test_campos_sao_lidos_pelo_icone_e_nao_pela_posicao(vagas):
    vaga = vagas["12210993"]
    assert vaga.salario == "R$ 3.000,00 a R$ 3.500,00"
    assert vaga.experiencia == "Entre 3 e 5 anos"
    assert vaga.escolaridade == "Ensino Superior"
    assert vaga.modalidade == "Home office"
    assert vagas["12149951"].experiencia is None   # card sem o chip de experiência
    for v in vagas.values():
        # a nota da empresa (ex.: "4,5") e o botão "Vagas semelhantes" não viram dado da vaga
        assert v.salario == "A combinar" or v.salario.startswith("R$ ")


def test_experiencia_so_existe_em_parte_das_vagas(vagas):
    assert Counter(v.experiencia for v in vagas.values()) == {
        None: 10,
        "Entre 3 e 5 anos": 5,
        "Entre 1 e 3 anos": 4,
        "Entre 5 e 10 anos": 1,
    }


def test_data_exata_do_atributo_oculto(vagas):
    assert vagas["12149951"].data_publicacao == datetime(2026, 11, 11, 6, 27)
    assert vagas["12209153"].data_publicacao == datetime(2026, 11, 11, 12, 23)
    assert all(v.data_publicacao is not None for v in vagas.values())


def test_descricao_mantem_o_espaco_entre_os_paragrafos(vagas):
    # o texto vem em <p> separados: sem separador viraria "São Paulo.Respons..."
    assert "São Paulo. Respons" in vagas["12209880"].descricao


# ------------------------------------------------------------------ modalidade


def test_modalidade_tem_um_icone_para_cada_valor(vagas):
    assert Counter(v.modalidade for v in vagas.values()) == {"Híbrido": 8, "Home office": 4, "Presencial": 8}
    assert vagas["12149951"].modalidade == "Híbrido"      # icon-house-and-building
    assert vagas["12210993"].modalidade == "Home office"  # icon-user-home
    assert vagas["12210878"].modalidade == "Presencial"   # icon-buildings


@pytest.mark.parametrize(
    "icone, texto",
    [
        ("icon-buildings", "Presencial"),
        ("icon-house-and-building", "Híbrido"),
        ("icon-user-home", "Home office"),
    ],
)
def test_cada_icone_de_modalidade_vira_o_texto_do_chip(icone, texto):
    jobs, _, _ = InfoJobsScraper._parsear_detalhado(_card("Analista de Dados", chips=[(icone, texto)]).encode())
    assert jobs[0].modalidade == texto


# ----------------------------------------------------------------------- Bronze


def test_bronze_guarda_o_html_original_de_cada_card(vagas, html):
    """O fragmento tem de ser idêntico ao card do portal, inclusive o trecho oculto da distância."""
    originais = {c["data-id"]: str(c) for c in BeautifulSoup(html, "html.parser").select(INFOJOBS_JOB_CARD)}
    assert set(originais) == set(vagas)
    for id_, vaga in vagas.items():
        assert vaga.raw_payload["html_fragment"] == originais[id_], id_


def test_bronze_conserva_distancia_e_coordenadas(vagas):
    com_coordenadas = [v for v in vagas.values() if 'data-vagalatitude="' in v.raw_payload["html_fragment"]]
    assert len(com_coordenadas) == 18  # as 2 vagas "Todo Brasil" não têm coordenadas
    assert all("js_divUserVagaDistance" in v.raw_payload["html_fragment"] for v in com_coordenadas)


def test_ler_o_local_nao_altera_o_card():
    card = _card("Analista de Dados")
    jobs, _, _ = InfoJobsScraper._parsear_detalhado(card.encode())
    fragmento = jobs[0].raw_payload["html_fragment"]
    assert jobs[0].localizacao == "São Paulo - SP"   # o texto oculto não entra no local...
    assert "data-vagalatitude" in fragmento          # ...mas continua no HTML guardado
    assert "0</span> Km de você." in fragmento


def test_extrair_local_trabalha_numa_copia_do_card():
    elemento = BeautifulSoup(_card("Analista de Dados"), "html.parser").select_one(INFOJOBS_JOB_CARD)
    antes = str(elemento)
    assert InfoJobsScraper._extrair_local(elemento) == "São Paulo - SP"
    assert str(elemento) == antes   # o card continua inteiro, com a distância e as coordenadas


@pytest.mark.parametrize("campo", ["titulo", "empresa", "localizacao", "descricao", "salario", "experiencia", "escolaridade", "modalidade"])
def test_nenhum_texto_inventado(vagas, campo):
    for vaga in vagas.values():
        valor = getattr(vaga, campo)
        if valor is None:
            continue
        texto_card = normalizar_espacos(BeautifulSoup(vaga.raw_payload["html_fragment"], "html.parser").get_text(" "))
        assert normalizar_espacos(valor) in texto_card, (vaga.id_externo, campo, valor)


# ------------------------------------------------------------------ senioridade


def test_senioridade_em_cascata_nas_20_vagas(vagas):
    assert set(vagas) == set(SENIORIDADE_ESPERADA)
    for id_, (nivel, origem) in SENIORIDADE_ESPERADA.items():
        assert vagas[id_].senioridade == nivel, id_
        assert vagas[id_].raw_payload["senioridade_origem"] == origem, id_


def test_cobertura_de_senioridade(vagas):
    por_origem = Counter(v.raw_payload["senioridade_origem"] for v in vagas.values())
    assert por_origem == {"titulo": 9, "experiencia_campo": 5, None: 6}


def test_titulos_reais_dao_o_mesmo_nivel_do_pipeline(vagas):
    """Quando a cascata usa o título, o nível é o do NormalizeService; quando não usa, o pipeline
    também não acha nível no título (senão a cascata passaria por cima de um título que tem nível)."""
    for vaga in vagas.values():
        do_pipeline = NormalizeService.normalizar_senioridade(vaga.titulo, de_titulo=True)
        if vaga.raw_payload["senioridade_origem"] == "titulo":
            assert vaga.senioridade == do_pipeline, vaga.titulo
        else:
            assert do_pipeline is None, vaga.titulo


def test_senioridade_nunca_e_o_texto_do_campo_de_experiencia(vagas):
    # o ícone "suitcase" é experiência ("Entre 1 e 3 anos"), nunca o nível em si
    assert not any("anos" in (v.senioridade or "") for v in vagas.values())


# ---------------------------------------------------------- cascata, cards sintéticos


def _card(titulo, *, data_id="1", chips=(), local="São Paulo - SP", descricao="Descrição da vaga.") -> str:
    itens = "".join(
        f'<div><svg class="icon {icone} icon-size-16"><use xlink:href="#x"></use></svg> {texto} </div>'
        for icone, texto in chips
    )
    return (
        f'<div class="js_vacancyLoad js_rowCard" data-id="{data_id}" data-href="/vaga-x__{data_id}.aspx">'
        '<div class="js_date" data-value="2026/11/11 05:15:00" hidden=""></div>'
        f'<a href="/vaga-x__{data_id}.aspx"><h2 class="js_vacancyTitle">{titulo}</h2></a>'
        '<div class="d-flex align-items-baseline"><div class="text-body"><a href="/empresa-x">Empresa X</a></div></div>'
        f'<div class="mb-8">{local}<span class="js_divUserVagaDistance" hidden="">, '
        '<span class="js_UserVagaDistance" data-vagalatitude="-23.6" data-vagalongitude="-46.6">0</span> Km de você.</span></div>'
        f'<div class="d-inline-flex flex-wrap mb-8 text-medium">{itens}</div>'
        f'<div class="text-medium">{descricao}</div>'
        "</div>"
    )


def _vaga(titulo, *, experiencia=None, descricao="Descrição da vaga."):
    chips = [("icon-suitcase", experiencia)] if experiencia else []
    jobs, _, _ = InfoJobsScraper._parsear_detalhado(_card(titulo, chips=chips, descricao=descricao).encode())
    return jobs[0]


@pytest.mark.parametrize(
    "titulo, experiencia, descricao, nivel, origem",
    [
        # o título manda, mesmo com experiência e descrição apontando para outro nível
        ("Analista de Dados Sênior", "Entre 1 e 3 anos", "Vaga para analista júnior.", "Sênior", "titulo"),
        ("Analista de Dados Jr", "Entre 5 e 10 anos", None, "Júnior", "titulo"),
        # sem nível no título, vale o nível escrito na descrição...
        ("Analista de Dados", "Entre 1 e 3 anos", "Procuramos Analista Sênior para o time.", "Sênior", "descricao_nivel"),
        # ...depois o campo de experiência
        ("Analista de Dados", "Entre 1 e 3 anos", "Descrição da vaga.", "Júnior", "experiencia_campo"),
        ("Analista de Dados", "Entre 3 e 5 anos", "Descrição da vaga.", "Pleno", "experiencia_campo"),
        ("Analista de Dados", "Entre 5 e 10 anos", "Descrição da vaga.", "Sênior", "experiencia_campo"),
        ("Analista de Dados", "Mais de 10 anos", "Descrição da vaga.", "Sênior", "experiencia_campo"),
        ("Auxiliar Administrativo", "Sem experiência", "Descrição da vaga.", "Júnior", "experiencia_campo"),
        ("Auxiliar Administrativo", "Só estágios", "Descrição da vaga.", "Estágio/Trainee", "experiencia_campo"),
        # por último, "N anos de experiência" escrito na descrição
        ("Analista de Dados", None, "Requisitos: 5+ anos de experiência com SQL.", "Sênior", "descricao_anos"),
        # sem nenhuma evidência: NULL, nunca um palpite
        ("Analista de Dados", None, "Descrição da vaga.", None, None),
        ("Desenvolvedor PL/SQL", None, "Descrição da vaga.", None, None),
    ],
)
def test_cascata_de_senioridade(titulo, experiencia, descricao, nivel, origem):
    vaga = _vaga(titulo, experiencia=experiencia, descricao=descricao)
    assert vaga.senioridade == nivel
    assert vaga.raw_payload["senioridade_origem"] == origem


def test_a_experiencia_continua_guardada_como_veio_do_portal():
    vaga = _vaga("Analista de Dados", experiencia="Entre 3 e 5 anos")
    assert vaga.experiencia == "Entre 3 e 5 anos"
    assert vaga.senioridade == "Pleno"
