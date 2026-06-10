"""
Testes unitários para SalaryService (Sprint 5)
Execução: pytest tests/test_salary_service.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from services.salary_service import SalaryService


class TestExtrairSalario:

    def test_faixa_com_rs(self):
        texto = "Salário: R$ 5.000,00 a R$ 8.000,00 mensais"
        resultado = SalaryService.extrair(texto)
        assert "R$" in resultado
        assert "5" in resultado

    def test_valor_unico_rs(self):
        texto = "Remuneração de R$ 6.500 por mês"
        resultado = SalaryService.extrair(texto)
        assert "R$" in resultado
        assert "6" in resultado

    def test_faixa_com_k(self):
        texto = "Faixa salarial entre 5k e 8k"
        resultado = SalaryService.extrair(texto)
        assert "R$" in resultado

    def test_a_combinar(self):
        texto = "Salário a combinar conforme experiência"
        assert SalaryService.extrair(texto) == "A combinar"

    def test_confidencial(self):
        texto = "Remuneração confidencial"
        assert SalaryService.extrair(texto) == "A combinar"

    def test_sem_informacao(self):
        assert SalaryService.extrair("Vaga para analista de dados")  == "Não informado"
        assert SalaryService.extrair("")                              == "Não informado"
        assert SalaryService.extrair(None)                           == "Não informado"

    def test_descricao_real_sem_salario(self):
        texto = (
            "Buscamos profissional com experiência em Python, SQL e AWS. "
            "Benefícios: VR, VT, plano de saúde."
        )
        assert SalaryService.extrair(texto) == "Não informado"