"""Carregador de seeds do dbt para uso no Python (fonte única de regras de negócio).

As listas de tecnologias monitoradas e termos de relevância são mantidas em
dbt/seeds/*.csv e consumidas tanto pelo dbt (seeds) quanto pelo Python (este
módulo). Assim não há duas listas divergentes em camadas diferentes.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=None)
def _projeto_raiz() -> Path:
    """Encontra a raiz do repositório (onde está dbt/seeds/)."""
    aqui = Path(__file__).resolve()
    # app/utils/seeds.py -> hub_vagas/
    for pai in [aqui.parent, aqui.parent.parent, aqui.parent.parent.parent]:
        if (pai / "dbt" / "seeds").is_dir():
            return pai
    return aqui.parent.parent.parent


@lru_cache(maxsize=None)
def carregar_seed(nome_arquivo: str) -> list[str]:
    """Lê uma seed CSV de dbt/seeds/ e devolve a primeira coluna como lista."""
    caminho = _projeto_raiz() / "dbt" / "seeds" / nome_arquivo
    valores: list[str] = []
    with caminho.open("r", encoding="utf-8") as f:
        linhas = f.read().strip().splitlines()
    # Primeira linha é o cabeçalho; ignora.
    for linha in linhas[1:]:
        celula = linha.split(",")[0].strip().strip('"')
        if celula:
            valores.append(celula)
    return valores
