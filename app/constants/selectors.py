"""Seletores CSS usados pelos parsers e pela navegação dos scrapers."""

VAGAS_JOB_CARD = "li.vaga"
VAGAS_TITLE = "a.link-detalhes-vaga"
VAGAS_COMPANY = "span.emprVaga"
VAGAS_SENIORITY = "span.nivelVaga"
VAGAS_POSITIONS = "span.qtdPosicoes"
# O local é <div class="vaga-local"> na maioria dos cards, mas vagas 100% home
# office usam <span class="vaga-local">. Por isso só a classe, sem a tag.
VAGAS_LOCATION = ".vaga-local"
# Balão "A empresa aceita candidaturas de ..." dentro do bloco do local.
VAGAS_LOCATION_NOISE = ".tooltip-place"
VAGAS_DESCRIPTION = "div.detalhes"
VAGAS_DATE = "span.data-publicacao"

INFOJOBS_JOB_CARD = "div.js_vacancyLoad"
INFOJOBS_TITLE = "h2"
INFOJOBS_COMPANY = "div.d-flex.align-items-baseline a"
INFOJOBS_METADATA = "div.d-inline-flex.flex-wrap div"
# Cada item do bloco de metadados traz um ícone que diz o que ele é.
# "icon-suitcase" é a EXPERIÊNCIA exigida (não a senioridade).
INFOJOBS_METADATA_ICONS = {
    "icon-money": "salario",
    "icon-suitcase": "experiencia",
    "icon-graduate-hat": "escolaridade",
    "icon-buildings": "modalidade",
}
INFOJOBS_LOCATION = "div.mb-8"
# Trecho oculto ", 0 Km de você." dentro do bloco do local.
INFOJOBS_LOCATION_NOISE = ".js_divUserVagaDistance"
INFOJOBS_DESCRIPTION = "div.text-medium"
# Data de publicação exata: <div class="js_date" data-value="2026/10/30 10:59:00">.
INFOJOBS_DATE = "div.js_date"
