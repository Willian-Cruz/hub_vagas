"""
Testes do JobRepository para os campos novos, NULL e deduplicação por
ID no portal e por conteúdo.

Estratégia igual à de test_job_repository.py: SessionLocal mockado, sem banco.
`first()` devolve, em ordem, o que cada consulta encontra (link, ID no portal,
conteúdo, tecnologias...); depois que a lista acaba, devolve None.

Execução: pytest tests/test_job_repository_dedup.py -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import IntegrityError

from database.job_model import Job
from repositories.job_repository import JobRepository, SALVA, DUPLICADA
from schemas.job_schema import JobSchema


def _vaga(**campos):
    base = dict(
        titulo="Engenheiro de Dados Jr",
        empresa="Empresa Teste",
        senioridade="Jr.",
        localizacao="sao paulo/sp",
        descricao="Experiência em Python e SQL.",
        link="https://www.vagas.com.br/vagas/v1/engenheiro-de-dados",
        origem="Vagas.com",
        id_externo="1",
    )
    base.update(campos)
    return JobSchema(**base)


def _sessao(*achados):
    """Sessão mockada; cada first() devolve o próximo item de `achados`."""
    proximos = iter(achados)
    session = MagicMock()
    session.query.return_value.filter.return_value.first.side_effect = (
        lambda: next(proximos, None)
    )
    return MagicMock(return_value=session), session


def _salvar(vaga, sessao_cls):
    with patch("repositories.job_repository.SessionLocal", sessao_cls):
        return JobRepository.salvar(vaga)


def _job_salvo(session):
    return session.add.call_args_list[0][0][0]


# ═══════════════════════════════════════════════════════════════
# NULL no lugar de "Não informado" e campos novos
# ═══════════════════════════════════════════════════════════════

class TestNullENovosCampos:

    def test_placeholders_do_portal_viram_none(self):
        sessao_cls, session = _sessao()
        vaga = _vaga(
            titulo="Analista de Dados",
            empresa="Confidencial",
            senioridade=None,
            localizacao="Localização não informada",
        )

        assert _salvar(vaga, sessao_cls) == SALVA

        job = _job_salvo(session)
        assert job.empresa is None
        assert job.localizacao is None
        assert job.senioridade is None
        assert job.chave_conteudo is None  # sem empresa/local não há chave

    def test_senioridade_inferida_do_titulo_quando_o_portal_nao_informa(self):
        sessao_cls, session = _sessao()
        vaga = _vaga(titulo="Engenheiro de Dados Sênior", senioridade=None)

        _salvar(vaga, sessao_cls)

        assert _job_salvo(session).senioridade == "Sênior"

    def test_senioridade_do_portal_tem_prioridade_sobre_o_titulo(self):
        sessao_cls, session = _sessao()
        vaga = _vaga(titulo="Engenheiro de Dados Sênior", senioridade="Pleno")

        _salvar(vaga, sessao_cls)

        assert _job_salvo(session).senioridade == "Pleno"

    def test_modalidade_inferida_do_local_home_office(self):
        sessao_cls, session = _sessao()
        vaga = _vaga(localizacao="100% Home Office", modalidade=None)

        _salvar(vaga, sessao_cls)

        job = _job_salvo(session)
        assert job.localizacao == "Remoto"
        assert job.modalidade == "Remoto"

    def test_salario_do_card_tem_prioridade_e_cai_na_descricao_se_faltar(self):
        sessao_cls, session = _sessao()
        _salvar(_vaga(salario="R$ 1.500,00", descricao="Salário R$ 9.000"), sessao_cls)
        assert _job_salvo(session).salario == "R$ 1.500,00"

        sessao_cls, session = _sessao()
        _salvar(_vaga(salario=None, descricao="Remuneração de R$ 6.500 por mês"), sessao_cls)
        assert "6.500" in _job_salvo(session).salario

    def test_sem_salario_em_lugar_nenhum_fica_none(self):
        sessao_cls, session = _sessao()

        _salvar(_vaga(salario=None, descricao="Vaga para analista de dados"), sessao_cls)

        assert _job_salvo(session).salario is None

    def test_persiste_os_campos_novos(self):
        sessao_cls, session = _sessao()
        publicada = datetime(2026, 10, 30, 10, 59, 0)
        vaga = _vaga(
            id_externo="11815887",
            data_publicacao=publicada,
            modalidade="Presencial",
            experiencia="Sem experiência",
            escolaridade="Ensino Superior",
            qtd_posicoes=2,
        )

        _salvar(vaga, sessao_cls)

        job = _job_salvo(session)
        assert job.id_externo == "11815887"
        assert job.data_publicacao == publicada
        assert job.modalidade == "Presencial"
        assert job.experiencia == "Sem experiência"
        assert job.escolaridade == "Ensino Superior"
        assert job.qtd_posicoes == 2

    def test_chave_de_conteudo_normalizada(self):
        sessao_cls, session = _sessao()
        vaga = _vaga(
            titulo="Engenheiro Civil Pl - V027803",
            empresa="Lyon Engenharia",
            localizacao="Guarujá / SP",
        )

        _salvar(vaga, sessao_cls)

        assert _job_salvo(session).chave_conteudo == (
            "vagas.com|engenheiro civil pl - v027803|lyon engenharia|guaruja - sp"
        )


# ═══════════════════════════════════════════════════════════════
# Deduplicação: link, ID no portal e conteúdo
# ═══════════════════════════════════════════════════════════════

class TestDeduplicacaoPorIdEConteudo:

    def test_mesmo_id_no_portal_com_link_diferente_e_duplicada(self):
        existente = MagicMock(spec=Job)
        sessao_cls, session = _sessao(None, existente)  # link não acha; ID acha

        assert _salvar(_vaga(), sessao_cls) == DUPLICADA

        session.add.assert_not_called()
        session.commit.assert_not_called()

    def test_mesma_vaga_republicada_com_outro_id_e_duplicada(self):
        # Caso real: "Engenheiro Civil Pl - V027803" da Lyon, IDs v2839939 e v2838771
        existente = MagicMock(spec=Job)
        sessao_cls, session = _sessao(None, None, existente)  # link, ID, conteúdo

        assert _salvar(_vaga(), sessao_cls) == DUPLICADA

        session.add.assert_not_called()
        session.commit.assert_not_called()

    def test_duplicada_por_conteudo_nao_herda_o_id_do_outro_anuncio(self):
        existente = Job(
            titulo="Engenheiro de Dados Jr",
            link="https://www.vagas.com.br/vagas/v0/antigo",
            origem="Vagas.com",
            empresa="Empresa Teste",
            localizacao="São Paulo - SP",
        )
        sessao_cls, session = _sessao(None, None, existente)

        assert _salvar(_vaga(id_externo="999"), sessao_cls) == DUPLICADA

        assert existente.id_externo is None

    def test_preenche_campos_nulos_da_vaga_ja_gravada(self):
        existente = Job(
            titulo="Engenheiro de Dados Jr",
            link="https://www.vagas.com.br/vagas/v1/engenheiro-de-dados",
            origem="Vagas.com",
            empresa=None,
            senioridade="Pleno",
        )
        sessao_cls, session = _sessao(existente)  # achada pelo link
        vaga = _vaga(data_publicacao=datetime(2026, 10, 30))

        assert _salvar(vaga, sessao_cls) == DUPLICADA

        session.commit.assert_called_once()
        assert existente.empresa == "Empresa Teste"
        assert existente.data_publicacao == datetime(2026, 10, 30)
        assert existente.id_externo == "1"
        session.add.assert_not_called()

    def test_nunca_sobrescreve_campo_ja_preenchido(self):
        existente = Job(
            titulo="Engenheiro de Dados Jr",
            link="https://www.vagas.com.br/vagas/v1/engenheiro-de-dados",
            origem="Vagas.com",
            empresa="Empresa Original",
            senioridade="Pleno",
            localizacao="Curitiba - PR",
        )
        sessao_cls, _ = _sessao(existente)

        _salvar(_vaga(), sessao_cls)  # traz Júnior, São Paulo, Empresa Teste

        assert existente.empresa == "Empresa Original"
        assert existente.senioridade == "Pleno"
        assert existente.localizacao == "Curitiba - PR"

    def test_violacao_do_indice_de_id_no_commit_retorna_duplicada(self):
        sessao_cls, session = _sessao()
        session.commit.side_effect = IntegrityError(
            "INSERT",
            {},
            Exception('duplicate key value violates unique constraint "uq_jobs_origem_id_externo"'),
        )

        assert _salvar(_vaga(), sessao_cls) == DUPLICADA

        session.rollback.assert_called_once()
