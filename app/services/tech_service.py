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
    def extrair(cls, descricao):

        if not descricao:
            return []

        descricao = descricao.lower()

        encontradas = []

        for tecnologia in cls.TECNOLOGIAS:

            if tecnologia in descricao:

                encontradas.append(tecnologia)

        return encontradas