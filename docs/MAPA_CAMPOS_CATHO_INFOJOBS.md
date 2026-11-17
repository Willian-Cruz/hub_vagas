# Mapa de campos — Catho e InfoJobs (cards da listagem)

> Base: páginas completas salvas em 11/11/2026 (20 vagas por portal; Catho: "analista de dados"; InfoJobs: "analista de dados em São Paulo"). Valores conferidos à mão no HTML.
> Código e testes: Catho → `app/scrapers/catho_parser.py` + `parser_utils.py` (testes em `test_catho_parser.py`); InfoJobs → o próprio `app/scrapers/infojobs_scraper.py`, já corrigido (testes em `test_infojobs_scraper_nov2026.py`); senioridade → `app/services/seniority_service.py` (testes em `test_seniority_service.py`). Fixtures: `catho_cards_2026_11.html` e `infojobs_cards_2026_11.html`.
> Layout de portal muda: se um teste quebrar, salve cards novos como fixture e ajuste os valores esperados.

## Catho — `li[data-offer-item="ID"]`

Hoje existe só o parser (`catho_parser.parse_cards`); não há `CathoScraper` no repositório.

| Campo | Onde está | Armadilha | Tratamento |
| --- | --- | --- | --- |
| id_externo | atributo `data-offer-item` (igual ao último trecho do href) | — | usar como `id_externo` |
| titulo, link | `h2.title_offer a` (texto e href relativo `/vagas/<slug>/<id>`) | — | `urljoin("https://www.catho.com.br", href)` |
| empresa | 1º `<span>` do `<p>` sem ícone dentro de `article` | anônima = "Empresa Confidencial" + `<button>Por que?</button>`: o texto do `<p>` vira "Empresa Confidencial Por que?" | ler só o `<span>`; confidencial → NULL |
| qtd_posicoes, localizacao | `<p>` com `.i_job_location`: `<strong>N vaga(s)</strong> - Cidade` | "5 vagas - Piracicaba" não é localização; o card não traz UF | regex `^(\d+) vagas? - (.+)$` |
| salario | `<p>` com `.i_salary` | "R$ 3.675 + 2 benefícios", "A partir de R$ 3.000,00", "Até R$ 2.000,00", "A Combinar" | separar benefícios; `parse_salario` devolve tipo/mín/máx |
| data | `span.tag`: "Publicada" ou "Atualizada" + "Hoje" / "Ontem" / "em dd/mm" | a classe `pub_ontem` também vem em "Publicada em 09/11"; sem ano; "Atualizada" não é publicação; a listagem é ordenada por data de atualização (`order: dataAtualizacao` no JS da página) | ler o texto; ano = o mais recente que não seja futuro; "Atualizada" vai para `data_atualizacao` |
| descrição, experiência, escolaridade, modalidade | **não existem no card** | — | só no detalhe da vaga |

**Detalhe da vaga (não testado).** O JS da página declara `urloffdet = https://oferta.catho.com.br/offer/{0}/d/j?ipo=42&iapo=1` e o template do detalhe renderiza a descrição completa (`o_ld`), "Tipo de contrato" e "Horário de trabalho". Não houve chamada: antes de usar, checar `robots.txt` e termos de uso (checklist da seção 10 do RESUMO).

## InfoJobs — `div.js_vacancyLoad[data-id]`

| Campo | Onde está | Armadilha | Tratamento |
| --- | --- | --- | --- |
| id_externo, link | `data-id` e `data-href` do `div.js_vacancyLoad` | `.js_rowCard` casa o card externo E o bloco interno (40 elementos para 20 vagas) | iterar em `.js_vacancyLoad` |
| data_publicacao | `.js_date[data-value="2026/11/11 06:27:00"]` (elemento `hidden`) | o texto visível é só "Hoje"; sem fuso; a ordem da página não é cronológica (01:55 seguido de 12:23) | `datetime.strptime(valor, "%Y/%m/%d %H:%M:%S")` |
| titulo | `.js_vacancyTitle` | — | — |
| empresa | `div.text-body` dentro de `.align-items-baseline` | links em 2 formatos: `/empresa-<slug>__<id>.aspx` (10/20) e `/<slug>` (9/20); anônima = "Empresa confidencial" sem link (1/20); a nota da empresa (ex.: 4,5) vem antes, em 15/20 | confidencial → NULL; não filtrar por `href` |
| localizacao | `div.mb-8` | `<span hidden>` ", 0 Km de você." (e as coordenadas da vaga, em `data-vagalatitude/longitude`, 18/20); aparece "Todo Brasil" (2/20) | remover `.js_divUserVagaDistance` **numa cópia** (no card vivo apaga a distância e as coordenadas da Bronze); conferir como a Silver trata "Todo Brasil" |
| salario, experiencia, escolaridade, modalidade | "chips" em `div.d-inline-flex`, identificados pelo ícone SVG | experiência só em 10/20 cards; a modalidade tem 3 ícones (`icon-house-and-building` = Híbrido 8/20, `icon-user-home` = Home office 4/20, `icon-buildings` = Presencial 8/20); o valor da experiência é "Entre 3 e 5 anos" (há também "Sem experiência" e "Só estágios") | mapear por ícone, nunca por posição |
| descricao | `div.text-medium` (filho direto) | resumo cortado em ~150 caracteres ("..."); o texto vem em `<p>` separados | `get_text(" ", strip=True)` |

O botão "Vagas semelhantes" fica no card externo, fora do bloco da vaga, e não é dado da vaga.

**Erros achados no `InfoJobsScraper` (rodado na página real em 12/11/2026) e correção.** Título, empresa, local, salário, data, experiência, escolaridade e descrição já saíam certos (20/20, conferidos contra uma leitura independente do HTML). Três problemas:

1. `modalidade` NULL em 12 de 20 vagas: o `selectors.py` só mapeava o ícone de Presencial. Corrigido com os ícones de Híbrido e Home office.
2. Bronze com HTML alterado: `_extrair_local` apagava o trecho oculto da distância no card original antes de o fragmento ser salvo (`raw_payload`), e o fragmento perdia a distância e as coordenadas (0/20, quando o HTML original tem em 18/20). Corrigido: o fragmento é tirado antes de ler os campos e o local é lido numa cópia.
3. `senioridade` sempre NULL (20/20). Agora sai da cascata abaixo: 14/20 preenchidas.

## Senioridade (cascata)

1. nível do portal → 2. título → 3. nível explícito na descrição → 4. campo de experiência → 5. "N anos de experiência" na descrição. Sem evidência = NULL. A origem (`portal`, `titulo`, `descricao_nivel`, `experiencia_campo`, `descricao_anos`) fica em `raw_payload["senioridade_origem"]` no InfoJobs (vai para `source_payload` na Bronze) e em `extra["senioridade_origem"]` no parser da Catho.

- **Regra do título = a do pipeline** (`NormalizeService.SENIORIDADE_MAP` e macro dbt `normalize_seniority`): mesmas palavras, mesma ordem (Júnior, Pleno, Sênior, Especialista, Coordenador, Liderança, Diretoria, Estágio). Com duas palavras de nível vale a primeira: "Pleno/Sênior" → Pleno, "Jr/Pleno" → Júnior, "Gerente Sênior" → Sênior; supervisor = Coordenador; head = Diretoria. Um teste compara a regra com o `NormalizeService` em dezenas de títulos e em todos os títulos reais das fixtures.
- **Diferenças propositais:** "PL/SQL", "PL-SQL", "PL SQL" e "PL-300" não são Pleno (o pipeline lê "PL" como Pleno); palavras a mais: mid-level, principal, aprendiz, intern, chief, vice-presidente, coord.
- Campo de experiência: mínimo < 3 anos → Júnior; 3–4 → Pleno; ≥ 5 → Sênior (`FAIXAS_EXPERIENCIA`, convenção ajustável); "Sem experiência" → Júnior; "Só estágios" → Estágio/Trainee.
- Cobertura nas 20 vagas: Catho 6/20 (só título; o card não tem descrição nem experiência); InfoJobs 14/20 (9 pelo título, 5 pelo campo de experiência). Nas 9 vagas da fixture antiga do InfoJobs (3/11/2026), todas de estágio, a senioridade é Estágio/Trainee pelo título.
- Entre os 5 cards do InfoJobs com título e experiência, 2 divergem (Sênior com 3–5 anos; Pleno com 5–10): por isso o título vem antes da faixa.
- As regras 3 e 5 (descrição) só foram exercitadas por testes sintéticos: nenhum dos 40 resumos reais continha esses padrões.

## Pendências

- Normalizador do pipeline (Python `NormalizeService` + macro dbt `normalize_seniority`, mudar os dois e rodar `python app/run_dbt.py build`): (a) "PL/SQL" vira Pleno por causa de `\y(pl|pleno)\y`; (b) o rótulo "Liderança" não é reconhecido como entrada (normalizar duas vezes devolve NULL; hoje o fallback pelo título cobre). Fazer como um passo separado, com testes.
- Receber HTML/JSON de amostra da Gupy e do Indeed. O repositório não tem scraper do Indeed nem da Catho (só o parser); a Gupy tem scraper, ainda sem a cascata (usar `classificar_senioridade`).
- Catho: decidir como coletar (endpoint de detalhe para a descrição) depois de checar `robots.txt`/termos.
- O `VagasScraper._extrair_local` tem o mesmo padrão do bug 2 (`decompose()` no card vivo antes de salvar o fragmento): o balão "A empresa aceita candidaturas de ..." some do HTML da Bronze.
- Decidir se `senioridade_origem` vira coluna (JobSchema → `select_bronze_jobs.sql` → `jobs.sql` → migration) ou fica no `source_payload`.
- "Empresa confidencial" não está em `PLACEHOLDERS`: o InfoJobs devolve NULL só porque o card não tem link; se o portal passar a linkar, viraria nome de empresa.
