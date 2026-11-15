"""Ponto de entrada para a TRANSFORMAÇÃO de dados via dbt.

Responsabilidade única: executar o pipeline dbt que transforma
os dados da camada Bronze para Silver e Gold.

Fluxo:
    Bronze (append-only) → Silver (normalização, deduplicação)
        → Gold (marts analíticos)

Uso:
    python app/transform.py              # build (modelos + testes)
    python app/transform.py source freshness  # verificar frescor das fontes
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_dbt import main as executar_dbt


def main() -> int:
    """Executa o pipeline de transformação via dbt."""
    print("Executando transformação de dados via dbt...")
    codigo = executar_dbt(["build"])
    if codigo == 0:
        print("Transformação concluída com sucesso!")
    else:
        print(f"Transformação falhou com código {codigo}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())