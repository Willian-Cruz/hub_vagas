"""Classificação de senioridade: título > nível explícito na descrição > campo de experiência > anos na descrição.

A regra do título segue o NormalizeService (mesmas palavras, mesma ordem), para o mesmo título
dar o mesmo nível em qualquer scraper e em qualquer camada; as diferenças são propositais e estão
nos testes "ao contrário do pipeline" e "palavras a mais".
"""
from __future__ import annotations

import pytest

from services.normalize_service import NormalizeService
from services.seniority_service import (
    COORDENADOR,
    DIRETORIA,
    ESPECIALISTA,
    ESTAGIO,
    JUNIOR,
    LIDERANCA,
    PLENO,
    SENIOR,
    Senioridade,
    anos_na_descricao,
    classificar_senioridade,
    nivel_no_texto,
    nivel_pelo_campo_de_experiencia,
    nivel_por_experiencia,
    parse_experiencia,
)


@pytest.mark.parametrize(
    "titulo, esperado",
    [
        # títulos reais da Catho e do InfoJobs (nov/2026)
        ("Analista de Dados Pleno", "Pleno"),
        ("ANALISTA DE SISTEMAS TI PLENO", "Pleno"),
        ("Analista de Dados JR", "Júnior"),
        ("Anl oper atacado jr análise de dados", "Júnior"),
        ("Analista de DTI Jr. (Dados e Automação", "Júnior"),
        ("ANALISTA DE INVENTÁRIO JR", "Júnior"),
        ("Analista Tributário Sênior", "Sênior"),
        ("ANALISTA DE MARKETING SÊNIOR", "Sênior"),
        ("Estágio inteligência de mercado / análise de dados (cod 46637)", "Estágio/Trainee"),
        ("Estágio em Pesquisa de Produtos, Análise de Imagens e Organização de Dados - Remoto", "Estágio/Trainee"),
        ("Analista de Dados e BI", None),
        ("Analista de Dados", None),
        ("Analista De Operações Batch (Control-M / Automic)", None),
        # variações comuns
        ("Analista de Dados Pl", "Pleno"),
        ("Analista de Dados Sr.", "Sênior"),
        ("Data Engineer Mid-Level", "Pleno"),
        ("Senior Data Analyst", "Sênior"),
        ("Trainee de Dados", "Estágio/Trainee"),
        ("Coordenador de BI", "Coordenador"),
        ("Supervisor de Dados", "Coordenador"),        # como no pipeline: supervisão = Coordenador
        ("Gerente de Dados", "Liderança"),
        ("Head de Analytics", "Diretoria"),            # como no pipeline: head = Diretoria
        ("Especialista em Dados", "Especialista"),
        ("Diretor de Dados", "Diretoria"),
        # duas palavras de nível no título: vale a primeira da lista (Júnior, Pleno, Sênior, ...)
        ("Analista de Dados Pleno/Sênior", "Pleno"),
        ("Analista de Dados Jr/Pleno", "Júnior"),
        ("Analista de Dados Pl/Sr", "Pleno"),
        ("Gerente de Dados Sênior", "Sênior"),
        ("Coordenador de BI Pleno", "Pleno"),
        # falsos positivos que precisam ser evitados
        ("Desenvolvedor PL/SQL", None),
        ("Desenvolvedor PL-SQL", None),
        ("Desenvolvedor PL SQL", None),
        ("Desenvolvedor PL / SQL", None),
        ("Analista Power BI (PL-300)", None),
        ("Desenvolvedor PL/SQL Sênior", "Sênior"),
        ("Analista de Plenária", None),
        ("", None),
        (None, None),
    ],
)
def test_nivel_no_titulo(titulo, esperado):
    assert nivel_no_texto(titulo) == esperado


@pytest.mark.parametrize(
    "titulo, esperado",
    [
        ("Lead Data Engineer", LIDERANCA),
        ("Data Manager", LIDERANCA),
        ("Líder de Dados", LIDERANCA),
        ("Estagiário de Dados", ESTAGIO),
        ("Aprendiz de Dados", ESTAGIO),
        ("Data Intern", ESTAGIO),
        ("Principal Data Engineer", ESPECIALISTA),
        ("Chief Data Officer", DIRETORIA),
        ("Vice-Presidente de Dados", DIRETORIA),
        ("VP de Dados", DIRETORIA),
        ("Coord. de BI", COORDENADOR),
    ],
)
def test_nivel_no_titulo_palavras_a_mais_que_o_pipeline_ou_iguais_a_ele(titulo, esperado):
    assert nivel_no_texto(titulo) == esperado


# Títulos em que a regra do pipeline (NormalizeService, espelhada na macro dbt normalize_seniority)
# e a desta cascata TÊM de concordar: o mesmo título dá o mesmo nível em qualquer scraper e camada.
@pytest.mark.parametrize(
    "titulo",
    [
        "Analista de Dados Pleno", "Analista de Dados JR", "Analista de Dados Sr.", "Senior Data Analyst",
        "Analista de Dados Pl", "Analista de Dados Pleno/Sênior", "Analista de Dados Jr/Pleno",
        "Gerente de Dados Sênior", "Coordenador de BI Pleno", "Coordenador de BI", "Supervisor de Dados",
        "Gerente de Dados", "Head de Analytics", "Lead Data Engineer", "Data Manager", "Diretor de Dados",
        "VP de Dados", "Especialista em Dados", "Estágio em Dados", "Estagiário de Dados Júnior",
        "Trainee de Dados", "Analista de Dados", "Analista de Plenária",
    ],
)
def test_mesma_resposta_do_normalizador_do_pipeline(titulo):
    assert nivel_no_texto(titulo) == NormalizeService.normalizar_senioridade(titulo, de_titulo=True)


@pytest.mark.parametrize("rotulo", [ESTAGIO, JUNIOR, PLENO, SENIOR, ESPECIALISTA, COORDENADOR, LIDERANCA, DIRETORIA])
def test_os_rotulos_sao_aceitos_como_entrada(rotulo):
    # "Liderança" não casa com nenhuma palavra da regra; sem isto o nível do portal se perderia
    assert nivel_no_texto(rotulo) == rotulo
    assert classificar_senioridade("Analista", nivel_portal=rotulo) == Senioridade(rotulo, "portal")


@pytest.mark.parametrize(
    "rotulo",
    [ESTAGIO, JUNIOR, PLENO, SENIOR, ESPECIALISTA, COORDENADOR, LIDERANCA, DIRETORIA],
)
def test_rotulo_gerado_sobrevive_a_normalizacao_do_pipeline(rotulo):
    # O JobRepository normaliza o que o scraper entrega; o rótulo tem de voltar igual.
    assert NormalizeService.normalizar_senioridade(rotulo) == rotulo


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Entre 3 e 5 anos", (3, 5)),
        ("Entre 1 e 3 anos", (1, 3)),
        ("Entre 5 e 10 anos", (5, 10)),
        ("1 a 3 anos", (1, 3)),
        ("2-4 anos", (2, 4)),
        ("Mais de 10 anos", (10, None)),
        ("Acima de 5 anos", (5, None)),
        ("5+ anos", (5, None)),
        ("Até 1 ano", (0, 1)),
        ("Menos de 1 ano", (0, 1)),
        ("Sem experiência", (0, 0)),
        ("2 anos", (2, None)),
        ("", None),
        (None, None),
        ("qualquer coisa", None),
    ],
)
def test_parse_experiencia(texto, esperado):
    assert parse_experiencia(texto) == esperado


@pytest.mark.parametrize(
    "anos_min, esperado",
    [(0, "Júnior"), (1, "Júnior"), (2, "Júnior"), (3, "Pleno"), (4, "Pleno"), (5, "Sênior"), (10, "Sênior"), (None, None)],
)
def test_nivel_por_experiencia(anos_min, esperado):
    assert nivel_por_experiencia(anos_min) == esperado


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Entre 1 e 3 anos", "Júnior"),
        ("Entre 3 e 5 anos", "Pleno"),
        ("Entre 5 e 10 anos", "Sênior"),
        ("Mais de 10 anos", "Sênior"),
        ("Sem experiência", "Júnior"),
        ("Só estágios", "Estágio/Trainee"),
        ("Somente estágio", "Estágio/Trainee"),
        ("Apenas estágios", "Estágio/Trainee"),
        ("", None),
        (None, None),
        ("qualquer coisa", None),
    ],
)
def test_nivel_pelo_campo_de_experiencia(texto, esperado):
    assert nivel_pelo_campo_de_experiencia(texto) == esperado


@pytest.mark.parametrize(
    "descricao, esperado",
    [
        ("Requisitos: 5+ anos de experiência com SQL", (5, None)),
        ("Experiência de 3 a 5 anos em BI", (3, 5)),
        ("3 a 5 anos de experiência com Power BI", (3, 5)),
        ("Mínimo de 2 anos de experiência na área", (2, None)),
        ("Mais de 8 anos de experiência em dados", (8, None)),
        ("Experiência mínima de 4 anos", (4, None)),
        ("Somos uma empresa com 20 anos de mercado", None),       # não é experiência exigida
        ("Pleno domínio de Excel", None),
        ("", None),
        (None, None),
    ],
)
def test_anos_na_descricao(descricao, esperado):
    assert anos_na_descricao(descricao) == esperado


def test_cascata_titulo_vence_experiencia():
    assert classificar_senioridade("Analista De Processos Pleno", experiencia="Entre 5 e 10 anos") == Senioridade("Pleno", "titulo")
    assert classificar_senioridade("Analista Tributário Sênior", experiencia="Entre 3 e 5 anos") == Senioridade("Sênior", "titulo")


def test_cascata_sem_titulo_usa_o_campo_de_experiencia():
    assert classificar_senioridade("Analista Financeiro", experiencia="Entre 3 e 5 anos") == Senioridade("Pleno", "experiencia_campo")
    assert classificar_senioridade("Consultor Comercial", experiencia="Entre 1 e 3 anos") == Senioridade("Júnior", "experiencia_campo")
    assert classificar_senioridade("Analista de Orçamento", experiencia="Entre 5 e 10 anos") == Senioridade("Sênior", "experiencia_campo")


def test_cascata_so_estagios_e_estagio_mas_o_titulo_vence():
    assert classificar_senioridade("Auxiliar Administrativo", experiencia="Só estágios") == Senioridade("Estágio/Trainee", "experiencia_campo")
    assert classificar_senioridade("Analista Júnior", experiencia="Só estágios") == Senioridade("Júnior", "titulo")


def test_cascata_nivel_do_portal_vem_primeiro():
    assert classificar_senioridade("Analista", nivel_portal="Sênior") == Senioridade("Sênior", "portal")
    assert classificar_senioridade("Analista Júnior", nivel_portal="Pleno") == Senioridade("Pleno", "portal")


def test_cascata_descricao_nivel_explicito():
    assert classificar_senioridade("Analista de Dados", descricao="Vaga para Analista de Dados Pleno, híbrido.") == Senioridade("Pleno", "descricao_nivel")
    assert classificar_senioridade("Analista de Dados", descricao="Nível: Sênior. Atuação em dados.") == Senioridade("Sênior", "descricao_nivel")


def test_cascata_descricao_explicita_vence_a_faixa_de_experiencia():
    resultado = classificar_senioridade("Analista", experiencia="Entre 1 e 3 anos", descricao="Procuramos Analista Sênior para o time.")
    assert resultado == Senioridade("Sênior", "descricao_nivel")


def test_cascata_descricao_anos_de_experiencia():
    assert classificar_senioridade("Analista de Dados", descricao="Requisitos: 5+ anos de experiência com SQL") == Senioridade("Sênior", "descricao_anos")
    assert classificar_senioridade("Analista de Dados", descricao="Experiência de 3 a 5 anos em BI") == Senioridade("Pleno", "descricao_anos")


def test_cascata_sem_evidencia_fica_nulo():
    assert classificar_senioridade("Analista de Dados") == Senioridade(None, None)
    assert classificar_senioridade("Analista de Dados", descricao="Pleno domínio de Excel. Empresa com 20 anos de mercado.") == Senioridade(None, None)
    assert classificar_senioridade(None) == Senioridade(None, None)
