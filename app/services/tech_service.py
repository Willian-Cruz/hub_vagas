import re


class TechnologyService:

    TECNOLOGIAS = [
        "python",
        "sql",
        "aws",
        "azure",
        "gcp",
        "spark",
        "airflow",
        "kafka",
        "docker",
        "kubernetes",
        "postgresql",
        "mysql",
        "oracle",
        "mongodb",
        "power bi",
        "tableau",
        "databricks",
        "snowflake",
    ]

    @classmethod
    def extrair(cls, descricao: str | None, titulo: str | None = None):
        """
        Extrai tecnologias mencionadas na descrição e/ou no título.

        Args:
            descricao: Texto da descrição da vaga
            titulo: Título da vaga (opcional)

        Returns:
            Lista de tecnologias encontradas (sem duplicatas, ordem alfabética)
        """
        textos = []
        if descricao:
            textos.append(descricao.lower())
        if titulo:
            textos.append(titulo.lower())

        if not textos:
            return []

        texto_completo = " ".join(textos)

        encontradas = []

        for tecnologia in cls.TECNOLOGIAS:
            padrao = rf"(?<!\w){re.escape(tecnologia)}(?!\w)"
            if re.search(padrao, texto_completo):
                encontradas.append(tecnologia)

        return sorted(encontradas)
