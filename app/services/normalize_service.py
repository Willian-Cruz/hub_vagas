import re
from typing import Optional

from utils.text_utils import valor_ou_none


class NormalizeService:
    """Padroniza campos de texto das vagas.

    Todos os métodos devolvem None quando não há informação aproveitável
    (vazio, placeholder do portal ou texto não reconhecido): o banco guarda NULL.
    """

    # _____________________________________________________
    # SENIORIDADE
    # Mapeamento: padrão regex → valor normalizado.
    # A ordem importa: o primeiro padrão que casar vence.
    # Todos usam limite de palavra (\b): sem isso "pl" casava dentro de
    # "Supply" e "sr" dentro de outras palavras.
    # _____________________________________________________
    SENIORIDADE_MAP = [
        (r"\b(?:jr|j[uú]nior)\b",                                   "Júnior"),   # 'Júnior/Trainee' → Júnior
        (r"\b(?:pl|pleno)\b",                                       "Pleno"),
        (r"\b(?:sr|s[eê]nior)\b",                                   "Sênior"),
        (r"\b(?:especialista|specialist)\b",                        "Especialista"),
        (r"\b(?:coordena[cç][aã]o|coordenador(?:a)?|coordinator|"
         r"supervis[aã]o|supervisor(?:a)?)\b",                      "Coordenador"),
        (r"\b(?:gerente|ger[eê]ncia|manager|l[ií]der|lider|leader|lead)\b", "Liderança"),
        (r"\b(?:diretor(?:a)?|diretoria|director|head|vp)\b",       "Diretoria"),
        (r"\b(?:trainee|est[aá]gi[oó]s?|estagi[aá]ri[oa]s?)\b",     "Estágio/Trainee"),
        (r"\bt[eé]cnic[oa]\b",                                      "Técnico"),
    ]

    # Níveis que só valem quando vêm do campo de nível do portal. No título,
    # "técnico" costuma ser o tipo de trabalho ("Suporte Técnico"), não o nível.
    _SO_NO_CAMPO = frozenset({"Técnico"})

    @classmethod
    def normalizar_senioridade(cls, valor, *, de_titulo: bool = False) -> Optional[str]:
        """
        Recebe qualquer string de senioridade e devolve um valor padronizado,
        ou None se não houver informação ou não reconhecer.

        `de_titulo=True` é para inferir o nível a partir do título da vaga.

        Exemplos:
            'Pleno/Sênior'  → 'Pleno'   (pega o primeiro match da lista)
            'Sr.'           → 'Sênior'
            'JÚNIOR'        → 'Júnior'
            'Supervisão/Coordenação' → 'Coordenador'
            ''              → None
        """
        texto = valor_ou_none(valor)
        if texto is None:
            return None

        texto = texto.lower()
        for padrao, resultado in cls.SENIORIDADE_MAP:
            if de_titulo and resultado in cls._SO_NO_CAMPO:
                continue
            if re.search(padrao, texto):
                return resultado
        return None

    ESTADOS_BR = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
        "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
        "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }

    _PREPOSICOES = frozenset({"de", "da", "do", "das", "dos", "e"})

    @classmethod
    def _capitalizar_cidade(cls, nome: str) -> str:
        """Title case que mantém preposições em minúsculas ("Rio de Janeiro")."""
        palavras = []
        for posicao, palavra in enumerate(nome.lower().split()):
            if posicao > 0 and palavra in cls._PREPOSICOES:
                palavras.append(palavra)
            elif palavra.startswith("d'") and len(palavra) > 2:
                palavras.append("d'" + palavra[2:].capitalize())  # Santa Bárbara d'Oeste
            else:
                palavras.append("-".join(parte.capitalize() for parte in palavra.split("-")))
        return " ".join(palavras)

    @classmethod
    def normalizar_localizacao(cls, valor) -> Optional[str]:
        #____________________________________________________________________________________

        # LOCALIZAÇÃO
        # Siglas de estados brasileiros válidos

        #____________________________________________________________________________________

        """
        Padroniza strings de localização para o formato 'Cidade - UF'
        ou 'Remoto' / 'Híbrido' quando aplicável. Devolve None sem informação.

        Exemplos:
            'são paulo - sp'        → 'São Paulo - SP'
            'São Paulo/SP'          → 'São Paulo - SP'
            'Rio de Janeiro/RJ'     → 'Rio de Janeiro - RJ'
            'Remoto'                → 'Remoto'
            '100% Home Office'      → 'Remoto'
            'Híbrido - RJ'          → 'Híbrido'
            'Localização não informada' → None
        """
        texto = valor_ou_none(valor)
        if texto is None:
            return None

        # Detecta modalidades especiais (prioridade sobre cidade/estado)
        texto_lower = texto.lower()
        if re.search(r"home.?office|remoto|remote|trabalho remoto", texto_lower):
            return "Remoto"
        if re.search(r"h[ií]brido|hybrid", texto_lower):
            return "Híbrido"

        # Normaliza separadores: "São Paulo/SP" → "São Paulo - SP"
        texto = re.sub(r"\s*/\s*", " - ", texto)
        texto = re.sub(r"\s*,\s*", " - ", texto)

        # Separa em partes pelo traço. Só separa o hífen "colado" quando ele vem
        # antes da UF final ("São Paulo-SP"); assim "Embu-Guaçu" continua inteiro.
        partes = [
            p.strip()
            for p in re.split(r"\s+-\s+|\s*-\s*(?=[A-Za-z]{2}\s*$)", texto)
            if p.strip()
        ]

        cidade = cls._capitalizar_cidade(partes[0]) if partes else ""

        # Tenta identificar a UF (última parte de 2 letras)
        uf = ""
        for parte in reversed(partes):
            candidato = parte.strip().upper()
            if candidato in cls.ESTADOS_BR:
                uf = candidato
                break

        if cidade and uf:
            return f"{cidade} - {uf}"
        return cidade or None

    @staticmethod
    def normalizar_modalidade(valor) -> Optional[str]:
        """Presencial / Híbrido / Remoto, ou None se não reconhecer."""
        texto = valor_ou_none(valor)
        if texto is None:
            return None
        texto = texto.lower()
        if re.search(r"home.?office|remoto|remote", texto):
            return "Remoto"
        if re.search(r"h[ií]brido|hybrid", texto):
            return "Híbrido"
        if re.search(r"presencial", texto):
            return "Presencial"
        return None

    #____________________________________________________________________________________
    # EMPRESA
    #____________________________________________________________________________________

    @staticmethod
    def normalizar_empresa(nome) -> Optional[str]:
        """Remove espaços extras. 'Confidencial' e vazio viram None."""
        return valor_ou_none(nome)
