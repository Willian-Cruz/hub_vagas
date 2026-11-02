"""
debug_vagas.py — diagnóstico do VagasScraper

Roda o browser em modo VISÍVEL para você ver o que está acontecendo,
tira um screenshot e despeja os seletores encontrados no HTML.

Uso:
    cd hub_vagas/app
    python debug_vagas.py
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL        = "https://www.vagas.com.br/vagas-de-engenheiro-de-dados"
SCREENSHOT = Path(__file__).parent.parent / "debug_screenshot.png"
HTML_DUMP  = Path(__file__).parent.parent / "debug_html.html"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

SELETORES_CANDIDATOS = [
    "li.vaga",
    "li[class*='vaga']",
    "[class*='vaga']",
    "article",
    ".job",
    ".job-card",
    "[class*='job']",
    ".vacancy",
    "[data-id]",
    "li",
]

print("=" * 60)
print("DEBUG — VagasScraper")
print("=" * 60)
print(f"URL: {URL}")
print(f"Screenshot: {SCREENSHOT}")
print(f"HTML dump:  {HTML_DUMP}")
print("=" * 60)
print("\nAbrindo browser VISIVEL (nao feche a janela)...")

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,   # modo visivel
        slow_mo=500,      # desacelera 0.5s entre acoes (mais facil de ver)
        args=["--disable-blink-features=AutomationControlled"],
    )

    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1920, "height": 1080},
        locale="pt-BR",
    )

    page = context.new_page()
    page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    print("\n[1/5] Acessando a URL...")
    try:
        page.goto(URL, timeout=40_000, wait_until="domcontentloaded")
        print("      OK — página carregada")
    except PlaywrightTimeout:
        print("      TIMEOUT ao carregar a página")
    except Exception as e:
        print(f"      ERRO: {e}")

    print("\n[2/5] Aguardando 5s para JS renderizar...")
    time.sleep(5)

    print("\n[3/5] Tirando screenshot...")
    page.screenshot(path=str(SCREENSHOT), full_page=False)
    print(f"      Salvo em: {SCREENSHOT}")

    print("\n[4/5] Testando seletores candidatos:")
    html = page.content()

    for seletor in SELETORES_CANDIDATOS:
        try:
            elementos = page.query_selector_all(seletor)
            qtd = len(elementos)
            status = f"{qtd} elemento(s)" if qtd > 0 else "0 — nao encontrado"
            print(f"      {seletor:<30} -> {status}")
        except Exception as e:
            print(f"      {seletor:<30} -> ERRO: {e}")

    print("\n[5/5] Salvando HTML completo...")
    HTML_DUMP.write_text(html, encoding="utf-8")
    print(f"      Salvo em: {HTML_DUMP}")

    # Mantém o browser aberto 10s para você ver a página
    print("\nFechando browser em 10s (ou feche a janela manualmente)...")
    time.sleep(10)
    browser.close()

print("\n" + "=" * 60)
print("Diagnóstico concluído.")
print("Compartilhe debug_screenshot.png para identificarmos o problema.")
print("=" * 60)
