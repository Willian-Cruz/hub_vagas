class NormalizeService:

    @staticmethod
    def normalizar_localizacao(local):

        local = local.upper()

        return local

    @staticmethod
    def normalizar_empresa(nome):

        return nome.strip()