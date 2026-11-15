# Plano de Implementação: Migração AnalyticsService → Gold e Aposentação da Tabela jobs

## Status Geral: ✅ CONCLUÍDO

Todas as três decisões do usuário foram implementadas e validadas:

1. **Pergunta 1 — Opção B**: ✅ Validado — migração do AnalyticsService para Gold e aposentação da tabela `jobs`  
2. **Pergunta 2 — Opção A**: ✅ Concluído — correção da Gupy (contrato NULL, relevância, cascata, fixture)  
3. **Pergunta 3 — Opção A**: ✅ Concluído — única fonte de verdade da senioridade

## Pilar 1 — Correção da Gupy (Opção A da Pergunta 2)
- **Arquivo**: `app/scrapers/gupy_scraper.py`
- **Mudanças**:
  - `_extrair_senioridade` agora usa `classificar_senioridade(titulo, descricao)` (cascata completa do `seniority_service.py`)
  - Retorna `None` em vez de `"Não informado"` quando não há evidência
  - Adicionado `RelevanceService.eh_relevante(v.titulo)` no `coletar()` (filtro de relevância, igual Vagas.com/InfoJobs)
  - Removido `_SENIORIDADE_HINT` regex antigo
- **Resultados**: ✅ 34 testes de scraper passando, ✅ 167 testes de seniority+normalize passando, ✅ 462 pytest totais passando

## Pilar 2 — Unificação da Senioridade (Opção A da Pergunta 3)
- **Nova macro**: `dbt/macros/classify_seniority_cascade.sql` — espelha `seniority_service.classificar_senioridade` com 5 estágios de fallback (nível explícito na descrição → campo de experiência → anos na descrição)
- **Modelo Silver atualizado**: `dbt/models/intermediate/jobs.sql` — adicionado `classify_seniority_cascade('senioridade_raw', 'titulo', 'experiencia', 'descricao')` como terceiro argumento do `coalesce` no CTE `normalized`
- **Lógica**: `coalesce(normalize_seniority(senioridade_raw), normalize_seniority(titulo, include_tecnico=false), classify_seniority_cascade(...))` — a cascata só rola quando o scraper não classificou (np e tt são NULL)
- **Princípio**: uma única fonte de verdade. Se o InfoJobs/classificador Python já preencheu `senioridade`, ele é usado. Se não, a cascata completa rola na Silver.

## Pilar 3 — Migração do AnalyticsService → Gold + Aposentação da tabela `jobs`
- **`app/services/analytics_service.py`**: Todas as 7 methods atualizadas para ler de `gold.mart_vagas` em vez de `jobs`:
  - `vagas_por_senioridade` → `FROM gold.mart_vagas`
  - `vagas_por_localizacao` → `FROM gold.mart_vagas`
  - `vagas_por_modalidade` → `FROM gold.mart_vagas`
  - `top_tecnologias` → usa `unnest(string_to_array(tecnologias, ','))` do mart Gold
  - `vagas_por_origem` → `FROM gold.mart_vagas`
  - `distribuicao_salarios` → `FROM gold.mart_vagas`
  - `resumo_geral` → `FROM gold.mart_vagas` para contagens principais; `technologies` table count mantido como query separada (tabela histórica, já populada)
- **`app/services/pipeline_service.py`**: Removida etapa 3 (persistência legacy `JobRepository.salvar`)
  - O pipeline agora tem 2 etapas: coleta + Bronze
  - Métricas `salvas` e `duplicadas` agora sempre 0 (mantidas no dicionário para compatibilidade)
  - Sucesso do pipeline depende apenas da Bronze OK + sem fontes com falha
- **Testes atualizados**: `app/tests/test_pipeline_service.py` — 2 testes ajustados para refletir novo comportamento (sem `JobRepository.salvar` mock)
- **Resultados**: ✅ 8/8 testes do pipeline_service passando, ✅ 462 pytest totais passando

## Resumo das Mudanças de Arquivos

| Arquivo | Tipo de mudança |
|---------|----------------|
| `app/scrapers/gupy_scraper.py` | Correção: cascata senioridade + filtro relevância |
| `dbt/macros/classify_seniority_cascade.sql` | Nova: macro dbt de cascata de senioridade |
| `dbt/models/intermediate/jobs.sql` | Atualizada: uso da nova macro no `coalesce` |
| `app/services/analytics_service.py` | Atualizada: queries de `jobs` → `gold.mart_vagas` |
| `app/services/pipeline_service.py` | Atualizada: remoção da etapa 3 (JobRepository.salvar) |
| `app/tests/test_pipeline_service.py` | Atualizada: testes adaptados ao novo pipeline |
| `README.md` | Pendente: atualizar seções de portas/arquitetura/próximos passos |

## Checklist de Validação ✅

- [x] `pytest tests/ -v` — 462 testes passando
- [x] `python app/run_dbt.py build` — estrutura dbt consistente (macro + modelo Silver)
- [x] Gupy scraper: relevância + cascata senioridade implementados e testados
- [x] Senioridade: macro dbt + modelo Silver implementados, fonte única de verdade
- [x] PipelineService: etapa 3 removida, métricas ajustadas
- [ ] Atualizar README.md (pendente - documentar novo estado)

## Próximos Passos

1. **Documentação**: Atualizar `README.md` com as mudanças realizadas (seções de portais, arquitetura, próximos passos)
2. **Verificação final**: Confirmar com o usuário que todas as três decisões foram atendidas conforme o esperado
3. **Fecha-plano**: Registrar conclusão no `.kilo/plan/`