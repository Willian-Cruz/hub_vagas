"""
Teste de segurança: varre fixtures em busca de padrões sensíveis.

Este teste garante que as fixtures HTML não contenham tokens, CSRF,
session IDs, chaves de API, scripts ou outros dados sensíveis que
poderiam ter vazado durante a coleta.
"""
import re
from pathlib import Path

import pytest


FIXTURES_DIR = Path("tests/fixtures")

# Padrões sensíveis que NÃO devem aparecer nas fixtures
SENSITIVE_PATTERNS = [
    (r"token", "token genérico"),
    (r"csrf", "CSRF token"),
    (r"sessionid", "session ID"),
    (r"authorization", "authorization header"),
    (r"api[_-]?key", "API key"),
    (r"<script", "tag script"),
    (r"password", "senha"),
    (r"secret", "segredo"),
    (r"access[_-]?token", "access token"),
    (r"refresh[_-]?token", "refresh token"),
    (r"bearer\s+[a-zA-Z0-9\-_]+", "bearer token"),
    (r"x-api-key", "x-api-key header"),
    (r"x-csrf-token", "x-csrf-token header"),
]

# Compila regexes uma vez
COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), desc) for p, desc in SENSITIVE_PATTERNS]


def _get_fixture_paths():
    return list(FIXTURES_DIR.glob("*.html"))


@pytest.mark.parametrize("fixture_path", _get_fixture_paths(), ids=lambda p: p.name)
def test_fixture_sem_padroes_sensiveis(fixture_path):
    """Cada fixture HTML não deve conter padrões sensíveis."""
    content = fixture_path.read_text(encoding="utf-8")

    for pattern, desc in COMPILED_PATTERNS:
        matches = pattern.findall(content)
        assert not matches, (
            f"Fixture {fixture_path.name} contém padrão sensível '{desc}': "
            f"{matches[:5]}{'...' if len(matches) > 5 else ''}"
        )


def test_fixtures_contem_cards():
    """Fixtures devem conter pelo menos um card de vaga (marcadores conhecidos)."""
    for fixture_path in FIXTURES_DIR.glob("*.html"):
        content = fixture_path.read_text(encoding="utf-8").lower()

        # Deve ter pelo menos um card (li, div com data-id, etc.)
        has_card = any(
            marker in content
            for marker in [
                'data-offer-item',  # Catho
                'data-id',  # InfoJobs
                'vaga-card',  # Vagas.com
                'js_vacancyload',  # InfoJobs
            ]
        )
        assert has_card, f"{fixture_path.name}: não parece conter cards de vagas"