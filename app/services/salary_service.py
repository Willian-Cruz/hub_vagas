import re
from typing import Optional


class SalaryService:
    """
    Tenta extrair informações salariais de campos de texto livre
    (título ou descrição da vaga).

    Retorna uma string formatada como:
        "R$ 5.000 - R$ 8.000"
        "R$ 6.000"
        "Não informado"

    Estratégia:
        1. Procura padrão de faixa: "R$ X a R$ Y" ou "R$ X - R$ Y"
        2. Procura valor único: "R$ X"
        3. Procura abreviações: "5k", "6.5k"
        4. Procura palavras-chave: "a combinar", "confidencial"
    """

    # ── Padrões em ordem do mais específico para o mais genérico ──

    # Faixa com "R$": "R$ 5.000,00 a R$ 8.000,00"  /  "R$5000-R$8000"
    _FAIXA_RS = re.compile(
        r"r\$\s*[\d.,]+(?:\s*(?:a|até|ao?|[-–])\s*r\$\s*[\d.,]+)?",
        re.IGNORECASE,
    )

    # Abreviação "k": "5k a 8k", "6.5k-9k"
    _FAIXA_K = re.compile(
        r"\d+(?:[.,]\d+)?k\s*(?:a|ao?|até|[-–])?\s*\d*(?:[.,]\d+)?k?",
        re.IGNORECASE,
    )

    # Palavras que indicam salário não divulgado
    _NAO_DIVULGADO = re.compile(
        r"a\s+combinar|confidencial|não\s+divulgado|sigiloso",
        re.IGNORECASE,
    )

    @classmethod
    def extrair(cls, texto: Optional[str]) -> str:
        """
        Extrai a faixa salarial de um texto.

        Args:
            texto: descrição ou qualquer campo de texto da vaga

        Returns:
            String com salário encontrado ou 'Não informado'
        """
        if not texto:
            return "Não informado"

        # Remove quebras de linha para facilitar o match
        texto_limpo = re.sub(r"\s+", " ", texto).strip()

        # 1. Verifica se é "a combinar" antes de tudo
        if cls._NAO_DIVULGADO.search(texto_limpo):
            return "A combinar"

        # 2. Busca padrão R$
        match_rs = cls._FAIXA_RS.search(texto_limpo)
        if match_rs:
            valor = match_rs.group(0).strip()
            # Normaliza espaços ao redor do separador
            valor = re.sub(r"\s*([-–]|a|ao|até)\s*", " - ", valor, flags=re.IGNORECASE)
            return cls._formatar(valor)

        # 3. Busca padrão "k" (ex: 5k a 8k)
        match_k = cls._FAIXA_K.search(texto_limpo)
        if match_k:
            return cls._converter_k(match_k.group(0))

        return "Não informado"

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _formatar(valor: str) -> str:
        """Garante letras maiúsculas no 'R$' e espaços corretos."""
        valor = re.sub(r"r\$", "R$", valor, flags=re.IGNORECASE)
        valor = re.sub(r"\s+", " ", valor).strip()
        return valor

    @staticmethod
    def _converter_k(valor: str) -> str:
        """
        Converte abreviações 'k' para valores monetários.
        Ex: '5k a 8k' → 'R$ 5.000 - R$ 8.000'
        """
        def k_para_reais(match):
            numero = float(match.group(1).replace(",", "."))
            return f"R$ {numero * 1000:,.0f}".replace(",", ".")

        resultado = re.sub(r"(\d+(?:[.,]\d+)?)k", k_para_reais, valor, flags=re.IGNORECASE)
        resultado = re.sub(r"\s*([-–]|a|ao|até)\s*", " - ", resultado, flags=re.IGNORECASE)
        return resultado.strip()