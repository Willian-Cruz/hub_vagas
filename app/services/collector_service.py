import time
from scrapers.vagas_scraper import VagasScraper
from scrapers.infojobs_scraper import InfoJobsScraper


class CollectorService:
    """
    Orquestra a execução de todos os scrapers.

    Responsabilidades:
        - Chamar cada scraper em sequência
        - Medir o tempo de coleta de cada um
        - Logar erros sem interromper os demais scrapers
        - Retornar a lista consolidada de vagas
    """

    SCRAPERS = [VagasScraper, InfoJobsScraper]

    @classmethod
    def coletar_todas_vagas(cls) -> list:

        todas_vagas = []

        for scraper in cls.SCRAPERS:

            print(f"\n{'─' * 50}")
            print(f"Iniciando: {scraper.__name__}")
            print(f"{'─' * 50}")

            inicio = time.time()

            try:
                resultado = scraper.coletar()
                duracao   = time.time() - inicio

                print(
                    f"\n✔ {scraper.__name__}: "
                    f"{len(resultado)} vagas coletadas "
                    f"em {duracao:.1f}s"
                )

                todas_vagas.extend(resultado)

            except Exception as erro:
                duracao = time.time() - inicio
                print(
                    f"\n✘ {scraper.__name__} falhou "
                    f"após {duracao:.1f}s: {erro}"
                )

        print(f"\n{'═' * 50}")
        print(f"Total geral: {len(todas_vagas)} vagas coletadas")
        print(f"{'═' * 50}\n")

        return todas_vagas