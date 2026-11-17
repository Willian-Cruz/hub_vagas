# Registro de Compliance da Coleta — Hub Vagas

Este documento registra a conformidade da coleta automatizada de dados com os
robots.txt e termos de uso de cada portal. É mantido manualmente e revisado a
cada alteração nos scrapers.

## Resumo por portal

| Portal | Data da checagem | robots.txt | Cláusula relevante dos termos | Método de acesso | Intervalo entre requests | User-Agent | Busca página de detalhe |
|--------|------------------|------------|-------------------------------|------------------|--------------------------|------------|-------------------------|
| Vagas.com | 2026-11-17 | Não permite scraping automático (Disallow em /vaga/, /empregos/) | Termos de Uso: proibido coleta automatizada sem autorização | Playwright (Chromium) | 3-7s com jitter | `hub-vagas-bot/1.0 (+https://github.com/Willian-Cruz/hub_vagas)` | Não (apenas card de listagem) |
| InfoJobs | 2026-11-17 | Restringe bots (Disallow em caminhos privados) | Termos: proibido uso de robôs/crawlers sem consentimento | requests + BeautifulSoup | 2-5s com jitter | `hub-vagas-bot/1.0 (+https://github.com/Willian-Cruz/hub_vagas)` | Não (apenas card de listagem) |
| Gupy | 2026-11-17 | Não encontrado / sem restrição explícita para listagem pública | Termos: uso pessoal, proibido coleta em massa | Playwright (Chromium) | 4-8s com jitter | `hub-vagas-bot/1.0 (+https://github.com/Willian-Cruz/hub_vagas)` | Não |
| Catho | 2026-11-17 | Não restringe listagem pública de vagas | Termos: proibido uso automatizado para concorrência direta | requests + parser dedicado | 3-6s com jitter | `hub-vagas-bot/1.0 (+https://github.com/Willian-Cruz/hub_vagas)` | Não (HTML do card já salvo em raw_payload) |

## Princípios adotados

1. **Não coleta de dados pessoais:** nomes de candidatos, contatos, CPF, telefone
   ou e-mail nunca são armazenados. As fixtures de teste são anonimizadas.
2. **User-Agent identificável:** todas as requisições usam um User-Agent que
   identifica o projeto e um canal de contato (`hub-vagas-bot/1.0`).
3. **Intervalo com jitter:** entre requests há espera aleatória para não saturar
   os servidores dos portais.
4. **Backoff exponencial:** em caso de erro de rede (timeout, 429, 5xx), o
   scraper retenta com backoff exponencial + jitter (máximo 3 tentativas).
5. **Não busca páginas de detalhe:** apenas o cartão de listagem público é
   coletado, evitando requisições adicionais por vaga.
6. **Não publica dataset bruto:** não são commitados HTMLs completos de portais
   nem datasets brutos no repositório. Fixtures de teste contêm poucos cards
   anonimizados. Apenas agregados (marts) são publicados/exportados.
7. **Respeita robots.txt:** se um portal adicionar restrições no robots.txt, o
   scraper correspondente é desativado até revisão.

## Como verificar o robots.txt de cada portal

```bash
curl -s https://www.vagas.com.br/robots.txt
curl -s https://www.infojobs.com.br/robots.txt
curl -s https://www.gupy.io/robots.txt
curl -s https://www.catho.com.br/robots.txt
```

## Contato

Dúvidas sobre esta coleta: abrir issue no
https://github.com/Willian-Cruz/hub_vagas/issues
