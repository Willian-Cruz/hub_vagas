"""
Testes do run_dbt: --project-dir e --profiles-dir são opções do subcomando.

Execução: pytest tests/test_run_dbt.py -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch

import run_dbt


def _comando(argumentos, tmp_path):
    perfil = tmp_path / "profiles.yml"
    perfil.write_text("x")
    executado = MagicMock(return_value=MagicMock(returncode=0))
    with patch.object(run_dbt, "_configurar_variaveis_dbt"), \
            patch.object(run_dbt.shutil, "which", return_value="dbt"), \
            patch.object(run_dbt, "DBT_PROFILE", perfil), \
            patch.object(run_dbt.subprocess, "run", executado):
        codigo = run_dbt.main(argumentos)
    return codigo, executado.call_args[0][0]


def test_opcoes_de_diretorio_vem_depois_do_subcomando(tmp_path):
    codigo, comando = _comando(["build"], tmp_path)

    assert codigo == 0
    assert comando[:2] == ["dbt", "build"]
    assert comando.index("build") < comando.index("--project-dir")
    assert comando.index("build") < comando.index("--profiles-dir")


def test_subcomando_composto_mantem_a_ordem(tmp_path):
    _, comando = _comando(["source", "freshness"], tmp_path)

    assert comando[:3] == ["dbt", "source", "freshness"]
    assert comando.index("freshness") < comando.index("--project-dir")


def test_sem_argumentos_executa_build(tmp_path):
    _, comando = _comando([], tmp_path)

    assert comando[:2] == ["dbt", "build"]
