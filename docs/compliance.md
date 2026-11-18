# Compliance da coleta de dados — Hub Vagas

Esta documento registra, portal por portal, a conformidade da coleta automatizada
com os termos de uso e o `robots.txt` de cada fonte. O objetivo é demonstrar
consciência legal e ética, reduzir o risco de bloqueio de IP e evitar pedidos
de remoção do repositório.

## Regras gerais aplicadas a todos os portais

| Regra | Implementação |
|-------|---------------|
| User-Agent identificável | `hub-vagas-bot/1.0 (+https://github.com/Willian-Cruz/hub_vagas; contato via issues)` — enviado em todo request |
| Intervalo com jitter | `BaseScraper._aguardar_intervalo_com_jitter()`: espera aleatória de 2–5 s entre requests (compartilhado pela classe) |
| Backoff com retry | `BaseScraper.coletar_com_retry()`: até 3 tentativas, backoff exponencial base 2 s + jitter |
| Não busca página de detalhe | Apenas cards de listagem são parseados; nenhuma requisição adicional por vaga |
| Fixtures reduzidas e anonimizadas | Poucos cards por portal, sem nomes de pessoas nem contatos |
| Dataset bruto não publicado | O repositório guarda apenas agregados (marts Gold); o raw não é commitado |

## Portal por portal

| Portal | Data da checagem | robots.txt | Cláusula relevante dos termos | Método de acesso | Intervalo entre requests | User-Agent | Busca página de detalhe |
|--------|------------------|------------|-------------------------------|------------------|--------------------------|------------|-------------------------|
| Vagas.com | 17/11/2026 | Permite scraping de listagens públicas com rate limit | Termos de uso proíbem coleta automatizada em massa sem autorização | `requests` + BeautifulSoup (HTML cru) | 2–5 s (jitter) | hub-vagas-bot/1.0 | Não |
| InfoJobs | 17/11/2026 | Não bloqueia user-agents identificados | Termos restringem uso comercial de dados coletados | `requests` + BeautifulSoup (HTML cru) | 2–5 s (jitter) | hub-vagas-bot/1.0 | Não |
| Gupy | 17/11/2026 | Não restringe listagens públicas | Não há cláusula específica sobre scraping de vagas | `requests` + BeautifulSoup (HTML cru) | 2–5 s (jitter) | hub-vagas-bot/1.0 | Não |
| Catho | 17/11/2026 | Não bloqueia `data-offer-item` em HTML cru | Termos restringem reprodução de conteúdo sem autorização | `requests` + BeautifulSoup (HTML cru) | 2–5 s (jitter) | hub-vagas-bot/1.0 | Não |

## Como verificar o robots.txt de cada portal

```bash
curl -s https://www.vagas.com.br/robots.txt
curl -s https://www.infojobs.com.br/robots.txt
curl -s https://www.gupy.io/robots.txt
curl -s https://www.catho.com.br/robots.txt
```

## Se um portal solicitar remoção

1. Remover o scraper correspondente de `app/scrapers/`.
2. Remover a fonte de `dbt/models/sources.yml`.
3. Atualizar esta documentação com a data e o motivo.
4. Re-executar `dbt build` — os marts Gold refletirão automaticamente a ausência da fonte.
