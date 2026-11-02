from database.job_tech_model import job_technologies
from services.job_service import JobService


def test_job_technology_association_has_composite_primary_key():
    assert [column.name for column in job_technologies.primary_key.columns] == [
        "job_id",
        "technology_id",
    ]


def test_legacy_job_service_imports_session_factory():
    assert callable(JobService.salvar)
