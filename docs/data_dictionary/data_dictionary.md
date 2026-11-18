# Data Dictionary — Hub Vagas

Dicionário de dados das tabelas e modelos do projeto, organizados por camada.

---

## Raw — `raw.job_observations`

| Coluna | Tipo | Nulo? | Descrição |
|--------|------|-------|-----------|
| `id` | BIGSERIAL | NOT NULL, PK | Identificador da observação (observation_id para linhagem) |
| `run_id` | UUID | NOT NULL | UUID da execução de coleta |
| `source` | TEXT | NOT NULL | Nome do portal (Vagas.com, InfoJobs, Gupy, Catho) |
| `source_job_id` | TEXT | | ID da vaga no portal (id_externo), quando disponível |
| `collected_at` | TIMESTAMPTZ | NOT NULL | Momento da coleta no portal |
| `ingested_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | Momento da persistência no banco |
| `scraper_version` | TEXT | | Versão do scraper utilizado na coleta |
| `payload_hash` | TEXT | NOT NULL | SHA-256 do raw_payload (dedup de retransmissão idêntica) |
| `raw_payload` | JSONB | NOT NULL | Payload bruto do scraper, sem normalização de negócio |
| `is_relevant` | BOOLEAN | NOT NULL DEFAULT TRUE | Resultado do filtro de relevância por título |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | Timestamp de criação do registro |

**Índices:** `(source, source_job_id, collected_at DESC)`, `(payload_hash)`, `(run_id)`

---

## Bronze — `bronze.scrape_runs`

| Coluna | Tipo | Nulo? | Descrição |
|--------|------|-------|-----------|
| `run_id` | UUID | NOT NULL, PK (composto) | UUID da execução |
| `source` | TEXT | NOT NULL, PK (composto) | Nome do portal |
| `status` | TEXT | NOT NULL | `success`, `partial`, `failed`, `empty` |
| `pages_processed` | INT | NOT NULL DEFAULT 0 | Páginas processadas |
| `jobs_found` | INT | NOT NULL DEFAULT 0 | Vagas encontradas |
| `error` | TEXT | | Mensagem de erro, se houver |
| `started_at` | TIMESTAMPTZ | NOT NULL | Início da execução |
| `finished_at` | TIMESTAMPTZ | NOT NULL | Término da execução |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | Criação do registro |

---

## Silver — `silver.jobs`

| Coluna | Tipo | Nulo? | Descrição |
|--------|------|-------|-----------|
| `raw_job_id` | INT | | FK para raw.job_observations.id |
| `origem` | TEXT | | Nome do portal |
| `link` | TEXT | | Link da vaga |
| `id_externo` | TEXT | | ID da vaga no portal |
| `titulo` | TEXT | NOT NULL | Título da vaga |
| `empresa` | TEXT | NULL | Nome da empresa |
| `senioridade` | TEXT | | Nível normalizado (9 valores) |
| `senioridade_inferida` | BOOLEAN | | True se senioridade foi derivada, não veio do portal |
| `localizacao` | TEXT | | Localização padronizada |
| `descricao` | TEXT | | Descrição da vaga |
| `salario_texto` | TEXT | | Salário como publicado |
| `salario_min` | NUMERIC | | Valor mínimo extraído |
| `salario_max` | NUMERIC | | Valor máximo extraído |
| `salario_tipo` | TEXT | | `faixa`, `exato`, `a_combinar`, `nao_informado` |
| `salario_inferido` | BOOLEAN | | True se salário foi derivado da descrição |
| `modalidade` | TEXT | | `Remoto`, `Híbrido`, `Presencial`, NULL |
| `experiencia` | TEXT | | Nível de experiência |
| `escolaridade` | TEXT | | Escolaridade exigida |
| `qtd_posicoes` | INT | | Quantidade de posições |
| `data_publicacao` | TIMESTAMPTZ | | Data de publicação (UTC) |
| `data_atualizacao` | TIMESTAMPTZ | | Data de atualização (apenas Catho) |
| `data_publicacao_precisao` | TEXT | | `hora`, `dia`, `estimada` |
| `chave_conteudo` | TEXT | | Chave de dedup cross-portal |
| `data_coleta` | TIMESTAMPTZ | | Momento da coleta |
| `ingested_at` | TIMESTAMPTZ | | Momento da persistência |
| `scraper_version` | TEXT | | Versão do scraper |
| `run_id` | UUID | | UUID da execução |
| `dedup_group_id` | TEXT | | Grupo de dedup |
| `first_seen_at` | TIMESTAMPTZ | | Primeira coleta do grupo |
| `last_seen_at` | TIMESTAMPTZ | | Última coleta do grupo |
| `is_canonical` | BOOLEAN | | True = linha mais recente do grupo |
| `dias_no_ar` | NUMERIC | | Diferença first_seen_at → last_seen_at em dias |
| `is_ativa` | BOOLEAN | | True se vista nos últimos 3 dias |
| `is_relevant` | BOOLEAN | | Resultado do filtro de relevância |
| `descricao_truncada` | BOOLEAN | | True se descrição termina em "..." ou ≤ 160 chars |
| `modalidade_origem` | TEXT | | `portal` ou `local` (origem da inferência de modalidade) |

---

## Gold — Marts analíticos

### `mart_vagas`

| Coluna | Descrição |
|--------|-----------|
| Todas as colunas de `silver.jobs` (apenas `is_canonical = true`) | Base principal para exportação e dashboard |

### `mart_vagas_por_dia`

| Coluna | Descrição |
|--------|-----------|
| `data_coleta` | Data da coleta |
| `origem` | Nome do portal |
| `observacoes` | Total de observações |
| `vagas_distintas` | Vagas distintas por link |
| `vagas_canonicas` | Vagas canônicas |
| `pct_com_descricao_completa` | % com descrição não truncada |

### `mart_salarios`

| Coluna | Descrição |
|--------|-----------|
| `origem` | Nome do portal |
| `senioridade` | Nível de senioridade |
| `total_vagas` | Total de vagas |
| `n_com_salario` | Vagas com salário informado |
| `pct_com_salario` | % com salário |
| `salario_min_medio` | Média do salário mínimo |
| `salario_max_medio` | Média do salário máximo |
| `salario_min_mediana` | Mediana do salário mínimo |
| `salario_max_mediana` | Mediana do salário máximo |

### `mart_demanda_tecnologias`

| Coluna | Descrição |
|--------|-----------|
| `tecnologia` | Nome da tecnologia (25 termos da seed) |
| `qtd_vagas` | Quantidade de vagas que mencionam a tecnologia |

### `mart_status_fontes`

| Coluna | Descrição |
|--------|-----------|
| `origem` | Nome do portal |
| `status` | Último status de execução |
| `finished_at` | Último horário de execução |
| `jobs_found` | Vagas encontradas na última execução |

### `mart_qualidade_campos`

| Coluna | Descrição |
|--------|-----------|
| `fonte` | Nome do portal |
| `campo` | Nome do campo (titulo, empresa, salario_texto, etc.) |
| `data_coleta` | Data da coleta |
| `total_vagas` | Total de vagas |
| `vagas_nao_nulas` | Vagas com o campo preenchido |

### `mart_vagas_por_origem_localidade`

| Coluna | Descrição |
|--------|-----------|
| `origem` | Nome do portal |
| `localizacao` | Localização da vaga |
| `senioridade` | Nível de senioridade |
| `qtd_vagas` | Quantidade de vagas |

---

## Regras gerais

- **Campo sem informação é `NULL`.** Nunca textos tipo "Não informado".
- **Dedup é por portal:** mesma vaga em dois portais conta duas vezes.
- **`a_combinar`** aparece apenas quando o portal informa explicitamente.
- **Datas em UTC** (`timestamptz`); conversão para São Paulo só na apresentação.
