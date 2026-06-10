import re 

class NormalizeService:
    # _____________________________________________________
    # SENIORIDADE
    # Mapeamento: padrão regex → valor normalizado
    # A ordem importa: mais específico primeiro.
    # _____________________________________________________
    SENIORIDADE_MAP = [
        
        (r"trainee|est[aá]gi[oó]|estagi[aá]rio", "Estágio/Trainee"),
        (r"jr\.?|j[uú]nior", "Júnior"),
        (r"pl\.?|pleno", "Pleno"),
        (r"sr\.?|s[eê]nior|senior", "Sênior"),
        (r"especialista|specialist", "Especialista"),
        (r"coordenador|coordinator", "Coordenador"),
        (r"gerente|manager|lider|l[ií]der|lead", "Liderança"),
        (r"diretor|director|head|vp\b", "Diretoria"),
    ]
    
    @classmethod
    def normalizar_senioridade(cls, valor:str) -> str:
        """
        Recebe qualquer string de senioridade e devolve um valor
        padronizado. Se não reconhecer, devolve 'Não informado'.
 
        Exemplos:
            'Pleno/Sênior'  → 'Pleno'   (pega o primeiro match)
            'Sr.'           → 'Sênior'
            'JÚNIOR'        → 'Júnior'
            ''              → 'Não informado'
        """
        if not valor or valor.strip().lower() in ("", "não informado", "nao informado"):
            return "Não informado"
        
        texto = valor.lower().strip()
        
        for padrao, resultado in cls.SENIORIDADE_MAP:
            if re.search(padrao, texto):
                return resultado
        return "Não informado"
    
    ESTADOS_BR = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
        "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
        "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
    
    @classmethod
    def normalizar_localizacao(cls, valor:str) -> str:
        #____________________________________________________________________________________
        
        # LOCALIZAÇÃO
        # Siglas de estados brasileiros válidos
        
        #____________________________________________________________________________________
        
        """
        Padroniza strings de localização para o formato 'Cidade - UF'
        ou 'Remoto' / 'Híbrido' quando aplicável.
 
        Exemplos:
            'são paulo - sp'        → 'São Paulo - SP'
            'São Paulo/SP'          → 'São Paulo - SP'
            'Remoto'                → 'Remoto'
            'Híbrido - RJ'          → 'Híbrido'
            'Home Office'           → 'Remoto'
        """
        if not valor or valor.strip().lower() in ("", "não informado", "nao informado"):
            return "Não informado"
 
        texto = valor.strip()
 
        # Detecta modalidades especiais (prioridade sobre cidade/estado)
        texto_lower = texto.lower()
        if re.search(r"home.?office|remoto|remote|trabalho remoto", texto_lower):
            return "Remoto"
        if re.search(r"h[ií]brido|hybrid", texto_lower):
            return "Híbrido"
 
        # Normaliza separadores: "São Paulo/SP" → "São Paulo - SP"
        texto = re.sub(r"\s*/\s*", " - ", texto)
        texto = re.sub(r"\s*,\s*", " - ", texto)
 
        # Separa em partes pelo traço
        partes = [p.strip() for p in texto.split("-")]
 
        # Capitaliza a cidade (title case)
        cidade = partes[0].strip().title() if partes else ""
 
        # Tenta identificar a UF (última parte de 2 letras)
        uf = ""
        for parte in reversed(partes):
            candidato = parte.strip().upper()
            if candidato in cls.ESTADOS_BR:
                uf = candidato
                break
 
        if cidade and uf:
            return f"{cidade} - {uf}"
        elif cidade:
            return cidade
        return "Não informado"
    
    #____________________________________________________________________________________
    # EMPRESA
    #____________________________________________________________________________________
    
    @staticmethod
    def normalizar_empresa(nome:str) -> str:
        """Remove espaços extras e capitaliza corretamente."""
        
        if not nome:
            return "Não informado"
        return nome.strip()