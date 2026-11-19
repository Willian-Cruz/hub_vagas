from app.services.tech_service import TechnologyService


def test_extrair_tecnologias_com_limites_de_palavra():
    tecnologias = TechnologyService.extrair(
        "Experiência com PostgreSQL, SQL e Power BI.",
        "Engenheiro de Dados"
    )

    assert tecnologias == ["postgresql", "power bi", "sql"]


def test_extrair_tecnologias_apenas_titulo():
    tecnologias = TechnologyService.extrair(
        None,
        "Python Developer com AWS"
    )

    assert tecnologias == ["aws", "python"]


def test_extrair_tecnologias_titulo_e_descricao():
    tecnologias = TechnologyService.extrair(
        "Experiência com Docker e Kubernetes.",
        "Engenheiro DevOps Azure"
    )

    assert tecnologias == ["azure", "docker", "kubernetes"]


def test_nao_confunde_sql_dentro_de_postgresql():
    assert TechnologyService.extrair("PostgreSQL") == ["postgresql"]


def test_descricao_vazia_nao_tem_tecnologias():
    assert TechnologyService.extrair("") == []


def test_titulo_vazio_nao_tem_tecnologias():
    assert TechnologyService.extrair(None, "") == []


def test_ambos_vazios_retorna_lista_vazia():
    assert TechnologyService.extrair(None, None) == []
