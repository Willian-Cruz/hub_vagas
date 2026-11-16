"""Scrapers de vagas de emprego."""

from .base_scraper import BaseScraper, ScrapeResult, ScrapeStatus
from .catho_scraper import CathoScraper
from .catho_parser import parse_cards, CardParseado
from .gupy_scraper import GupyScraper
from .infojobs_scraper import InfoJobsScraper
from .vagas_scraper import VagasScraper

__all__ = [
    "BaseScraper",
    "ScrapeResult",
    "ScrapeStatus",
    "CathoScraper",
    "parse_cards",
    "CardParseado",
    "GupyScraper",
    "InfoJobsScraper",
    "VagasScraper",
]