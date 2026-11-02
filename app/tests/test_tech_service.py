from services.tech_service import TechnologyService


def test_extrair_tecnologias_com_limites_de_palavra():
    tecnologias = TechnologyService.extrair(
        "Experiência com PostgreSQL, SQL e Power BI."
    )

    assert tecnologias == ["sql", "postgresql", "power bi"]


def test_nao_confunde_sql_dentro_de_postgresql():
    assert TechnologyService.extrair("PostgreSQL") == ["postgresql"]


def test_descricao_vazia_nao_tem_tecnologias():
    assert TechnologyService.extrair("") == []
