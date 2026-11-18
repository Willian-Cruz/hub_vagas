# Contratos de Dados — Hub Vagas

Este documento formaliza as estruturas e expectativas de dados entre scrapers,
persistência e transformações, evitando que alterações nas fontes externas
contaminem as etapas seguintes.

---

## 1. Princípios gerais

| Princípio | Descrição |
|-----------|-----------|
| Campo sem informação é `NULL` | Nunca o texto "Não informado", "Confidencial" ou "Localização não informada". |
| NULL ≠ campo ausente ≠ desconhecido ≠ não aplicável | São estados distintos e não devem ser tratados como equivalentes. |
| Dado inferido é marcado | Flags `senioridade_inferida`, `salario_inferido` indicam quando o campo foi derivado, não veio do portal. |
| Campo adicional inesperado é aceito | Fontes externas podem evoluir; não se rejeita automaticamente campos extras. |
| Mudanças incompatíveis são detectadas | Testes de contrato falham antes de contaminar os modelos analíticos. |

---

## 2. Contrato de entrada — `JobSchema` (Pydantic)

Campos produzidos pelos scrapers e consumidos pelo `JobRepository.salvar()`.

### Campos obrigatórios

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `titulo` | `str` | Título da vaga. Obrigatório em todo scraper. |
| `link` | `str` | URL da vaga. Obrigatório, usado como fallback de identidade. |
| `origem` | `str` | Nome do portal. Valores aceitos: `Vagas.com`, `InfoJobs`, `Gupy`, `Catho`. |

### Campos opcionais

| Campo | Tipo | Descrição | Semântica quando NULL |
|-------|------|-----------|----------------------|
| `empresa` | `Optional[str]` | Nome da empresa. | Portal não informou ou seletor falhou. |
| `senioridade` | `Optional[str]` | Nível de senioridade bruto (ex: "Pleno", "Sênior"). | Portal não informou no card. |
| `localizacao` | `Optional[str]` | Localização bruta (ex: "São Paulo - SP"). | Portal não informou. |
| `descricao` | `Optional[str]` | Descrição da vaga (resumo do card). | Portal não traz descrição no card. |
| `salario` | `Optional[str]` | Salário como publicado (ex: "R$ 3.000,00"). | Portal não informou salário no card. |
| `detail_url` | `Optional[str]` | URL da página de detalhe para deep scraping. | Scraper não suporta ou não encontrou. |
| `id_externo` | `Optional[str]` | ID da vaga no portal, estável entre coletas. | Portal não expõe ID estável. |
| `data_publicacao` | `Optional[datetime]` | Data de publicação da vaga (UTC). | Portal não informou data. |
| `modalidade` | `Optional[str]` | Presencial / Híbrido / Remoto. | Portal não informou. |
| `experiencia` | `Optional[str]` | Campo de experiência do portal (ex: "Entre 3 e 5 anos"). | Não é senioridade; nunca vira nível. |
| `escolaridade` | `Optional[str]` | Escolaridade exigida. | Portal não informou. |
| `qtd_posicoes` | `Optional[int]` | Quantidade de posições. | Portal não informou. |
| `is_relevant` | `bool` | Resultado do filtro de relevância por título. | Sempre preenchido (default `True`). |
| `motivo_relevancia` | `Optional[str]` | Motivo do descarte quando `is_relevant=False`. | Preenchido apenas quando não relevante. |
| `raw_payload` | `dict[str, Any]` | Payload bruto do scraper, sem normalização. | Sempre preenchido (dict vazio mínimo). |
| `scraper_version` | `Optional[str]` | Versão do scraper utilizado (linhagem de dados). | Default `"1.0.0"`. |

### Semântica de NULL em `JobSchema`

| Estado | Significado | Exemplo |
|--------|-------------|---------|
| `None` | Campo ausente ou não informado pela fonte | `empresa=None` quando o card não traz empresa |
| `""` (vazio) | Não usado; sempre convertido para `None` | — |
| Valor preenchido | Informação extraída da fonte | `senioridade="Pleno"` |

---

## 3. Contrato de persistência — `raw.job_observations`

Colunas gravadas pelo `JobRepository.salvar()` e consumidas pelo dbt staging.

| Coluna | Tipo | Nulo? | Origem | Descrição |
|--------|------|-------|--------|-----------|
| `id` | bigserial | NOT NULL, PK | Auto | Identificador da observação (observation_id para linhagem) |
| `run_id` | uuid | NOT NULL | Pipeline | UUID da execução de coleta |
| `source` | text | NOT NULL | Scraper | Nome do portal |
| `source_job_id` | text | | Scraper | ID da vaga no portal (id_externo) |
| `collected_at` | timestamptz | NOT NULL | Pipeline | Momento da coleta no portal |
| `ingested_at` | timestamptz | NOT NULL DEFAULT now() | Pipeline | Momento da persistência no banco |
| `scraper_version` | text | | Scraper | Versão do coletor utilizado |
| `payload_hash` | text | NOT NULL | Repository | SHA-256 do `raw_payload` (dedup de retransmissão idêntica) |
| `raw_payload` | jsonb | NOT NULL | Scraper | Payload bruto, sem normalização de negócio |
| `is_relevant` | boolean | NOT NULL DEFAULT true | RelevanceService | Resultado do filtro de relevância por título |
| `created_at` | timestamptz | NOT NULL DEFAULT now() | Pipeline | Timestamp de criação do registro |

### Regras de persistência

- **Append-only:** nenhuma linha é apagada ou sobrescrita.
- **Dedup:** mesma `(source, source_job_id, payload_hash)` não é regravada.
- **Transação:** INSERT é feito dentro de transação; falha faz rollback e retorna `"erro"`.

---

## 4. Contrato de saída — Silver e Gold

### Silver — `silver.jobs`

Produzida pelo dbt a partir da raw. Todas as linhas são mantidas (dedup marca `is_canonical`).

| Coluna | Tipo | Nulo? | Descrição |
|--------|------|-------|-----------|
| `raw_job_id` | int | | FK para raw.job_observations.id |
| `origem` | text | | Nome do portal |
| `link` | text | | Link da vaga |
| `titulo` | text | NOT NULL | Título normalizado |
| `empresa` | text | | NULL se não informado |
| `senioridade` | text | | Nível normalizado (9 valores aceitos) |
| `senioridade_inferida` | boolean | | True se derivada do título/descrição |
| `localizacao` | text | | Padronizada ("Cidade - UF") |
| `descricao` | text | | Resumo do card |
| `salario_texto` | text | | Salário como publicado |
| `salario_min` | numeric | | Valor mínimo extraído |
| `salario_max` | numeric | | Valor máximo extraído |
| `salario_tipo` | text | | `faixa`, `exato`, `a_combinar`, `nao_informado` |
| `salario_inferido` | boolean | | True se derivado da descrição |
| `modalidade` | text | | `Remoto`, `Híbrido`, `Presencial`, NULL |
| `data_publicacao` | timestamptz | | UTC |
| `data_publicacao_precisao` | text | | `hora`, `dia`, `estimada` |
| `data_atualizacao` | timestamptz | | Apenas Catho preenche |
| `data_coleta` | timestamptz | | Momento da coleta |
| `ingested_at` | timestamptz | | Momento da persistência |
| `scraper_version` | text | | Versão do scraper |
| `run_id` | uuid | | UUID da execução |
| `dedup_group_id` | text | | Grupo de dedup cross-portal |
| `first_seen_at` | timestamptz | | Primeira coleta do grupo |
| `last_seen_at` | timestamptz | | Última coleta do grupo |
| `is_canonical` | boolean | | True = linha mais recente do grupo |
| `dias_no_ar` | numeric | | Diferença first_seen_at → last_seen_at em dias |
| `is_ativa` | boolean | | True se vista nos últimos 3 dias |
| `is_relevant` | boolean | | Resultado do filtro de relevância |

### Gold — `gold.mart_*`

Os marts agregam a Silver (apenas `is_canonical = true`). Nenhum contrato de saída garante completude de 100% dos campos; consumidores devem tratar NULLs.

---

## 5. Semântica de datas, moeda e identificadores

### Datas e timestamps

- Todos os timestamps são armazenados em **UTC** (`timestamptz`).
- Conversão para São Paulo (`America/Sao_Paulo`) é feita **apenas na apresentação** (Power BI, relatórios).
- `data_publicacao`: momento em que a vaga foi publicada no portal.
- `data_coleta`: momento em que o scraper coletou a vaga.
- `ingested_at`: momento em que o registro foi persistido no banco.
- `data_atualizacao`: momento em que o portal informou atualização (apenas Catho).
- Nunca substituir data ausente por data fictícia.

### Identificadores

- `id` (raw): surrogate key, autoincremental.
- `run_id`: UUID gerado pelo pipeline, rastreia a execução completa.
- `source_job_id` / `id_externo`: ID da vaga no portal de origem.
- `link`: URL canônica da vaga, usada como fallback de identidade.
- `dedup_group_id`: chave de conteúdo cross-portal (título + empresa + localização).

### Moeda

- Valores monetários são armazenados como texto original (`salario_texto`) e numérico parseado (`salario_min`, `salario_max`).
- Não são feitas conversões monetárias automáticas.
- `salario_tipo` classifica: `faixa`, `exato`, `a_combinar`, `nao_informado`.
- "A combinar" **não** é inferido da descrição; aparece apenas quando o portal informa explicitamente.

---

## 6. Evolução dos contratos

### Mudanças compatíveis (não quebram consumidores)

| Mudança | Tratamento |
|---------|------------|
| Inclusão de campo opcional na raw | Aceito; dbt staging ignora se não mapeado |
| Inclusão de campo opcional em `JobSchema` | Aceito; default definido |
| Adição de valor aceito em campo categórico | Aceito; testes de `accepted_values` atualizados |
| Renomeação de campo internamente no scraper | Não afeta contrato se `JobSchema` não mudar |

### Mudanças incompatíveis (devem ser detectadas antes do merge)

| Mudança | Detecção |
|---------|----------|
| Remoção de campo obrigatório de `JobSchema` | Teste de contrato Pydantic falha |
| Mudança de tipo de coluna em `raw.job_observations` | `assert_contrato_python_dbt_columns.sql` + teste de tipo |
| Remoção de coluna esperada pelo dbt staging | `dbt build` falha (coluna não encontrada) |
| Mudança de semântica de campo (ex: `senioridade` vira texto livre) | Testes de `accepted_values` falham |

### Política de versionamento

- Não há versionamento formal de contrato (sem `v1`, `v2` nos schemas).
- Mudanças incompatíveis são comunicadas via PR com descrição do impacto.
- Antes de remover ou renomear um campo, deve-se:
  1. Adicionar o novo campo ao lado do antigo.
  2. Atualizar todos os consumidores (scraper → raw → dbt → mart).
  3. Remover o campo antigo apenas após confirmar que nenhum consumidor depende dele.

---

## 7. Validação e testes de contrato

| Teste | O que valida | Severidade |
|-------|--------------|------------|
| `assert_contrato_python_dbt_columns.sql` | Colunas obrigatórias presentes em `raw.job_observations` | error |
| Teste Pydantic `JobSchema` | Campos obrigatórios, tipos, valores default | error |
| `assert_silver_sem_placeholder.sql` | Campo sem informação nunca vira texto "Não informado" | error |
| `assert_silver_valores_validos.sql` | Campos categóricos contêm apenas valores permitidos | error |
| `assert_normalize_seniority.sql` | Senioridade: PL/SQL, PL-300 não são Pleno; "Liderança" aceita | error |
| `assert_seniority_edge_cases.sql` | Casos de borda da normalização de senioridade | error |

---

## 8. Exemplo de rastreabilidade (linhagem)

Para responder "de onde veio este dado?" a partir de um indicador do Gold:

```
Gold mart_demanda_tecnologias (Python: 42%)
    │
    ▼
Silver silver.jobs (vagas com Python na descrição/título)
    │  ├─ run_id → execução de coleta
    │  ├─ source → portal de origem
    │  ├─ scraper_version → versão do coletor
    │  └─ ingested_at → momento da persistência
    │
    ▼
Raw raw.job_observations (payload bruto JSONB)
    │  ├─ payload_hash → identificador do conteúdo coletado
    │  └─ raw_payload → HTML do card / dados da API
```

Não é necessário armazenar uma lista de IDs dentro de cada linha agregada do Gold; basta que existam os relacionamentos (`run_id`, `raw_job_id`) para reconstruir o caminho.
