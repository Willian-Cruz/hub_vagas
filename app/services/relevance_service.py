"""Filtro de relevância: separa vagas do escopo do hub das que só casaram na busca.

Os portais buscam por palavras soltas ("engenheiro" OU "dados"), então uma busca
por "engenheiro de dados" devolve engenharia civil, estágio em segurança do
trabalho, executivo de vendas etc. O critério aqui é o TÍTULO: a vaga só passa se
o título citar algum termo de dados.
"""
import re

from utils.text_utils import sem_acentos


class RelevanceService:
    # Termos sem acento e em minúsculas; casam como palavra inteira.
    TERMOS_TITULO = (
        "dados",
        "data",
        "database",
        "analytics",
        "business intelligence",
        "bi",
        "etl",
        "dbt",
        "machine learning",
        "inteligencia artificial",
        "ia",
        "dba",
        "sql",
        "python",
        "spark",
        "airflow",
        "databricks",
        "snowflake",
        "bigquery",
    )

    @classmethod
    def eh_relevante(cls, titulo) -> bool:
        if not titulo:
            return False
        texto = sem_acentos(str(titulo)).casefold()
        padrao = r"\b(?:" + "|".join(re.escape(t) for t in cls.TERMOS_TITULO) + r")\b"
        return re.search(padrao, texto) is not None

    @classmethod
    def separar(cls, vagas) -> tuple[list, list]:
        """Devolve (relevantes, descartadas), preservando a ordem."""
        relevantes, descartadas = [], []
        for vaga in vagas:
            (relevantes if cls.eh_relevante(vaga.titulo) else descartadas).append(vaga)
        return relevantes, descartadas
