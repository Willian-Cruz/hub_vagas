"""
Testes de contrato para JobSchema (Pydantic).

Valida:
- Campos obrigatórios (titulo, link, origem) são exigidos.
- Campos opcionais defaultam para None quando ausentes.
- Tipos inválidos são rejeitados.
- Valores default (is_relevant, scraper_version, raw_payload).
- Semântica de NULL: campo ausente vira None, nunca texto falso.

Execução: pytest app/tests/test_job_schema.py -v
"""
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.job_schema import JobSchema


def _vaga_valida():
    return JobSchema(
        titulo="Engenheiro de Dados Pleno",
        link="https://example.com/vaga/123",
        origem="InfoJobs",
    )


class TestCamposObrigatorios:
    """Campos obrigatórios: ausência deve levantar ValidationError."""

    def test_sem_titulo_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(link="https://example.com/v/1", origem="InfoJobs")

    def test_sem_link_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(titulo="Vaga X", origem="InfoJobs")

    def test_sem_origem_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(titulo="Vaga X", link="https://example.com/v/1")

    def test_titulo_vazio_e_rejeitado(self):
        # Título obrigatório não pode ser vazio ou apenas espaços
        with pytest.raises(ValidationError):
            JobSchema(titulo="", link="https://example.com/v/1", origem="InfoJobs")
        with pytest.raises(ValidationError):
            JobSchema(titulo="   ", link="https://example.com/v/1", origem="InfoJobs")

    def test_link_vazio_e_rejeitado(self):
        with pytest.raises(ValidationError):
            JobSchema(titulo="Vaga X", link="", origem="InfoJobs")

    def test_origem_vazio_e_rejeitado(self):
        with pytest.raises(ValidationError):
            JobSchema(titulo="Vaga X", link="https://example.com/v/1", origem="")

    def test_link_tipo_invalido_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(titulo="Vaga X", link=123, origem="InfoJobs")


class TestCamposOpcionais:
    """Campos opcionais defaultam para None quando ausentes."""

    def test_empresa_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.empresa is None

    def test_senioridade_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.senioridade is None

    def test_localizacao_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.localizacao is None

    def test_descricao_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.descricao is None

    def test_salario_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.salario is None

    def test_detail_url_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.detail_url is None

    def test_id_externo_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.id_externo is None

    def test_data_publicacao_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.data_publicacao is None

    def test_modalidade_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.modalidade is None

    def test_experiencia_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.experiencia is None

    def test_escolaridade_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.escolaridade is None

    def test_qtd_posicoes_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.qtd_posicoes is None

    def test_motivo_relevancia_none_por_default(self):
        vaga = _vaga_valida()
        assert vaga.motivo_relevancia is None

    def test_raw_payload_dict_vazio_por_default(self):
        vaga = _vaga_valida()
        assert vaga.raw_payload == {}


class TestValoresDefault:
    """Valores default definidos no contrato."""

    def test_is_relevant_default_true(self):
        vaga = _vaga_valida()
        assert vaga.is_relevant is True

    def test_scraper_version_default(self):
        vaga = _vaga_valida()
        assert vaga.scraper_version == "1.0.0"

    def test_is_relevant_pode_ser_false(self):
        vaga = JobSchema(
            titulo="Vaga X",
            link="https://example.com/v/1",
            origem="InfoJobs",
            is_relevant=False,
            motivo_relevancia="titulo_sem_termo_de_dados",
        )
        assert vaga.is_relevant is False
        assert vaga.motivo_relevancia == "titulo_sem_termo_de_dados"


class TestTiposInvalidos:
    """Tipos inválidos devem ser rejeitados pelo Pydantic."""

    def test_titulo_nao_string_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(titulo=123, link="https://example.com/v/1", origem="InfoJobs")

    def test_link_nao_string_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(titulo="Vaga X", link=None, origem="InfoJobs")

    def test_origem_nao_string_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(titulo="Vaga X", link="https://example.com/v/1", origem=None)

    def test_qtd_posicoes_nao_inteiro_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(
                titulo="Vaga X",
                link="https://example.com/v/1",
                origem="InfoJobs",
                qtd_posicoes="duas",
            )

    def test_data_publicacao_nao_datetime_falha(self):
        with pytest.raises(ValidationError):
            JobSchema(
                titulo="Vaga X",
                link="https://example.com/v/1",
                origem="InfoJobs",
                data_publicacao=["não", "é", "uma", "data"],
            )


class TestCamposPreenchidos:
    """Campos preenchidos devem ser preservados exatamente como vieram."""

    def test_todos_campos_preenchidos(self):
        agora = datetime(2026, 11, 17, 10, 30, 0, tzinfo=UTC)
        vaga = JobSchema(
            titulo="Engenheiro de Dados Sênior",
            empresa="Empresa LTDA",
            senioridade="Sênior",
            localizacao="São Paulo - SP",
            descricao="Vaga para engenheiro de dados com Python e SQL.",
            salario="R$ 8.000,00 a R$ 12.000,00",
            link="https://example.com/vaga/999",
            origem="Vagas.com",
            detail_url="https://example.com/vaga/999/detalhes",
            id_externo="ext-999",
            data_publicacao=agora,
            modalidade="Híbrido",
            experiencia="Entre 3 e 5 anos",
            escolaridade="Ensino Superior Completo",
            qtd_posicoes=2,
            is_relevant=True,
            motivo_relevancia=None,
            raw_payload={"html_fragment": "<li>...</li>"},
            scraper_version="1.1.0",
        )
        assert vaga.titulo == "Engenheiro de Dados Sênior"
        assert vaga.empresa == "Empresa LTDA"
        assert vaga.senioridade == "Sênior"
        assert vaga.localizacao == "São Paulo - SP"
        assert vaga.descricao == "Vaga para engenheiro de dados com Python e SQL."
        assert vaga.salario == "R$ 8.000,00 a R$ 12.000,00"
        assert vaga.link == "https://example.com/vaga/999"
        assert vaga.origem == "Vagas.com"
        assert vaga.detail_url == "https://example.com/vaga/999/detalhes"
        assert vaga.id_externo == "ext-999"
        assert vaga.data_publicacao == agora
        assert vaga.modalidade == "Híbrido"
        assert vaga.experiencia == "Entre 3 e 5 anos"
        assert vaga.escolaridade == "Ensino Superior Completo"
        assert vaga.qtd_posicoes == 2
        assert vaga.is_relevant is True
        assert vaga.motivo_relevancia is None
        assert vaga.raw_payload == {"html_fragment": "<li>...</li>"}
        assert vaga.scraper_version == "1.1.0"


class TestSemanticaNull:
    """Campo ausente vira None, nunca texto falso ("Não informado")."""

    def test_campo_ausente_nao_vira_texto_falso(self):
        vaga = _vaga_valida()
        assert vaga.empresa is None
        assert vaga.empresa != "Não informado"
        assert vaga.empresa != "Confidencial"
        assert vaga.localizacao is None
        assert vaga.localizacao != "Localização não informada"
        assert vaga.salario is None
        assert vaga.salario != "A combinar"
