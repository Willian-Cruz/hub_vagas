import re
from typing import Optional

from utils.seeds import carregar_seed


class TechnologyService:

    _TECNOLOGIAS_CACHE: list[str] | None = None

    @classmethod
    def _tecnologias(cls) -> list[str]:
        if cls._TECNOLOGIAS_CACHE is None:
            cls._TECNOLOGIAS_CACHE = carregar_seed("tecnologias_monitoradas.csv")
        return cls._TECNOLOGIAS_CACHE

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

        for tecnologia in cls._tecnologias():
            padrao = rf"(?<!\w){re.escape(tecnologia)}(?!\w)"
            if re.search(padrao, texto_completo):
                encontradas.append(tecnologia)

        return sorted(encontradas)
