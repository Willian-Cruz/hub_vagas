from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """
    Contrato base para todos os scrapers do hub_vagas.

    MAX_PAGES: limite de páginas por execução — protege contra
    loops infinitos e sobrecarga nos servidores dos portais.
    Cada subclasse pode sobrescrever conforme o portal permitir.
    """

    MAX_PAGES = 10

    @classmethod
    @abstractmethod
    def coletar(cls) -> list:
        """
        Coleta vagas do portal e retorna uma lista de JobSchema.
        Deve percorrer todas as páginas disponíveis até MAX_PAGES.
        """
        pass

    @classmethod
    def _log(cls, msg: str) -> None:
        """Log padronizado com o nome do scraper."""
        print(f"[{cls.__name__}] {msg}")