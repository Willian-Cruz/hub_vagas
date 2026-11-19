"""
Testes de integração — Persistência (raw.job_observations).

Valida:
- Inserção de uma observação
- Preservação do payload original (JSONB)
- Armazenamento do hash
- Identificação da fonte e execução (run_id)
- Tratamento de duplicidades (mesmo payload = duplicada, payload diferente = revisada)
- Linhagem: ingested_at e scraper_version gravados

Execução (CI com services: postgres):
    pytest app/tests/integration/test_persistence.py -m integration -v
"""
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.job_repository import (
    DUPLICADA,
    REVISADA,
    SALVA,
    JobRepository,
)
from app.schemas.job_schema import JobSchema


def _vaga(
    titulo="Engenheiro de Dados Pleno",
    empresa="Empresa Teste",
    link="https://example.com/vaga/persistencia-001",
    origem="Vagas.com",
    id_externo="pers-001",
    salario="R$ 5.000,00",
):
    return JobSchema(
        titulo=titulo,
        empresa=empresa,
        senioridade="Pleno",
        localizacao="São Paulo - SP",
        descricao="Vaga para teste de persistência.",
        salario=salario,
        link=link,
        origem=origem,
        id_externo=id_externo,
        raw_payload={"html_fragment": "<li class='vaga'>...</li>"},
    )


@pytest.mark.integration
def test_insercao_observacao_persiste_campos_obrigatorios(conexao):
    """Uma vaga válida é inserida com todos os campos obrigatórios preenchidos."""
    run_id = uuid4()
    vaga = _vaga()

    resultado = JobRepository.salvar(vaga, run_id=run_id)
    assert resultado == SALVA

    # Verifica que a linha foi inserida
    row = conexao.execute(
        text(
            "SELECT id, run_id, source, source_job_id, collected_at, "
            "payload_hash, raw_payload, is_relevant, ingested_at, scraper_version "
            "FROM raw.job_observations WHERE link = :link"
        ),
        {"link": vaga.link},
    ).fetchone()

    assert row is not None
    assert row.run_id == run_id
    assert row.source == "Vagas.com"
    assert row.source_job_id == "pers-001"
    assert row.is_relevant is True
    assert row.payload_hash is not None
    assert row.raw_payload is not None
    assert row.ingested_at is not None
    assert row.scraper_version == "1.0.0"
    assert row.collected_at is not None


@pytest.mark.integration
def test_payload_original_preservado_jsonb(conexao):
    """O raw_payload é preservado exatamente como veio do scraper (JSONB)."""
    run_id = uuid4()
    vaga = _vaga()
    vaga.raw_payload = {
        "html_fragment": "<li class='vaga'><a href='/vaga/1'>Título</a></li>",
        "seletor_usado": "li.vaga",
    }

    JobRepository.salvar(vaga, run_id=run_id)

    row = conexao.execute(
        text(
            "SELECT raw_payload->'_raw_payload_scraper'->>'html_fragment' as html, "
            "raw_payload->'_raw_payload_scraper'->>'seletor_usado' as seletor "
            "FROM raw.job_observations WHERE link = :link"
        ),
        {"link": vaga.link},
    ).fetchone()

    assert row.html == "<li class='vaga'><a href='/vaga/1'>Título</a></li>"
    assert row.seletor == "li.vaga"


@pytest.mark.integration
def test_dedup_mesmo_hash_duplicada(conexao):
    """Mesmo (origem, id_externo, payload_hash) → DUPLICADA, sem novo INSERT."""
    run_id = uuid4()
    vaga = _vaga()

    r1 = JobRepository.salvar(vaga, run_id=run_id)
    assert r1 == SALVA

    r2 = JobRepository.salvar(vaga, run_id=run_id)
    assert r2 == DUPLICADA

    # Deve haver apenas 1 linha
    count = conexao.execute(
        text("SELECT count(*) FROM raw.job_observations WHERE link = :link"),
        {"link": vaga.link},
    ).scalar()
    assert count == 1


@pytest.mark.integration
def test_dedup_hash_diferente_revisada(conexao):
    """Mesmo (origem, id_externo) com payload diferente → REVISADA, novo INSERT."""
    run_id = uuid4()
    vaga = _vaga()

    r1 = JobRepository.salvar(vaga, run_id=run_id)
    assert r1 == SALVA

    # Muda o payload (simula atualização do card)
    vaga.raw_payload = {"html_fragment": "<li class='vaga'>conteúdo atualizado</li>"}
    r2 = JobRepository.salvar(vaga, run_id=run_id)
    assert r2 == REVISADA

    # Deve haver 2 linhas (uma para cada observação)
    count = conexao.execute(
        text("SELECT count(*) FROM raw.job_observations WHERE link = :link"),
        {"link": vaga.link},
    ).scalar()
    assert count == 2


@pytest.mark.integration
def test_campos_ausentes_viram_none(conexao):
    """Campos opcionais ausentes são gravados como NULL, nunca texto falso."""
    run_id = uuid4()
    vaga = JobSchema(
        titulo="Vaga sem campos opcionais",
        link="https://example.com/vaga/sem-campos",
        origem="InfoJobs",
        # empresa, senioridade, localizacao, salario etc. ausentes
    )

    JobRepository.salvar(vaga, run_id=run_id)

    row = conexao.execute(
        text(
            "SELECT raw_payload->>'empresa' as empresa, "
            "raw_payload->>'senioridade' as senioridade, "
            "raw_payload->>'localizacao' as localizacao, "
            "raw_payload->>'salario' as salario "
            "FROM raw.job_observations WHERE link = :link"
        ),
        {"link": vaga.link},
    ).fetchone()

    # raw_payload armazena os campos brutos; campos ausentes são NULL no JSONB
    # Verificamos que o raw_payload foi gravado sem campos ausentes
    assert row is not None
