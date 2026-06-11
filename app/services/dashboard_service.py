import json
import os
from datetime import datetime
from services.analytics_service import AnalyticsService

COLORS = [
    "#4361ee",
    "#3a0ca3",
    "#7209b7",
    "#f72585",
    "#4cc9f0",
    "#4895ef",
    "#560bad",
    "#480ca8",
    "#b5179e",
    "#f77f00",
    "#2ec4b6",
    "#e63946",
    "#06d6a0",
    "#118ab2",
    "#ffd166",
]


def _df_to_chart(df, label_col="label", value_col="total"):
    """Converte um DataFrame em dicionários de labels e dados para Chart.js."""
    labels = df[label_col].tolist()
    data = df[value_col].tolist()
    colors = COLORS[: len(labels)]
    return labels, data, colors


class DashboardService:

    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "dashboard")
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "dashboard.html")

    @classmethod
    def gerar(cls):
        """
        Ponto de entrada principal.
        Coleta todos os dados e gera o arquivo HTML.
        """
        print("Coletando dados do banco...")

        resumo = AnalyticsService.resumo_geral()
        senioridade = AnalyticsService.vagas_por_senioridade()
        localizacao = AnalyticsService.vagas_por_localizacao(top_n=10)
        modalidade = AnalyticsService.vagas_por_modalidade()
        tecnologias = AnalyticsService.top_tecnologias(top_n=15)
        origem = AnalyticsService.vagas_por_origem()
        salarios = AnalyticsService.distribuicao_salarios()

        print("Gerando HTML...")

        # Serializa tudo para JSON (será injetado no JS do HTML)
        dados = {
            "resumo": resumo,
            "senioridade": {
                "labels": senioridade["label"].tolist(),
                "data": senioridade["total"].tolist(),
            },
            "localizacao": {
                "labels": localizacao["label"].tolist(),
                "data": localizacao["total"].tolist(),
            },
            "modalidade": {
                "labels": modalidade["label"].tolist(),
                "data": modalidade["total"].tolist(),
            },
            "tecnologias": {
                "labels": tecnologias["label"].tolist(),
                "data": tecnologias["total"].tolist(),
            },
            "origem": {
                "labels": origem["label"].tolist(),
                "data": origem["total"].tolist(),
            },
            "salarios": {
                "labels": salarios["label"].tolist(),
                "data": salarios["total"].tolist(),
            },
        }

        html = cls._build_html(dados)

        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        with open(cls.OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Dashboard gerado em: {cls.OUTPUT_FILE}")
        return cls.OUTPUT_FILE

    # ─────────────────────────────────────────────────────────────
    # TEMPLATE HTML
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def _build_html(cls, dados: dict) -> str:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        resumo = dados["resumo"]
        cores = json.dumps(COLORS)
        dados_json = json.dumps(dados, ensure_ascii=False)

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hub Vagas — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg:       #0f172a;
    --surface:  #1e293b;
    --border:   #334155;
    --text:     #e2e8f0;
    --muted:    #94a3b8;
    --accent:   #4361ee;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 24px;
    min-height: 100vh;
  }}
  header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 28px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
  }}
  header h1 {{ font-size: 1.6rem; color: #fff; }}
  header h1 span {{ color: var(--accent); }}
  header p  {{ font-size: 0.8rem; color: var(--muted); }}
 
  /* ── KPI cards ── */
  .kpis {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }}
  .kpi {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
  }}
  .kpi .value {{ font-size: 2rem; font-weight: 700; color: var(--accent); }}
  .kpi .label {{ font-size: 0.8rem; color: var(--muted); margin-top: 4px; }}
 
  /* ── Grid de gráficos ── */
  .grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }}
  .card.wide {{ grid-column: span 2; }}
  .card h2 {{
    font-size: 0.95rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .05em;
    margin-bottom: 16px;
  }}
  .chart-wrap {{ position: relative; height: 280px; }}
  .chart-wrap.tall {{ height: 340px; }}
 
  @media (max-width: 768px) {{
    .grid {{ grid-template-columns: 1fr; }}
    .card.wide {{ grid-column: span 1; }}
  }}
</style>
</head>
<body>
 
<header>
  <div>
    <h1>Hub Vagas <span>Analytics</span></h1>
    <p>Mercado de trabalho em Dados &amp; Tecnologia — Brasil</p>
  </div>
  <p>Atualizado em {agora}</p>
</header>
 
<!-- KPIs -->
<div class="kpis">
  <div class="kpi">
    <div class="value">{resumo["total_vagas"]:,}</div>
    <div class="label">Vagas coletadas</div>
  </div>
  <div class="kpi">
    <div class="value">{resumo["total_empresas"]:,}</div>
    <div class="label">Empresas únicas</div>
  </div>
  <div class="kpi">
    <div class="value">{resumo["total_techs"]:,}</div>
    <div class="label">Tecnologias mapeadas</div>
  </div>
  <div class="kpi">
    <div class="value">{resumo["total_portais"]}</div>
    <div class="label">Portais integrados</div>
  </div>
</div>
 
<!-- Gráficos -->
<div class="grid">
 
  <div class="card">
    <h2>Vagas por Senioridade</h2>
    <div class="chart-wrap"><canvas id="chartSenioridade"></canvas></div>
  </div>
 
  <div class="card">
    <h2>Modalidade de Trabalho</h2>
    <div class="chart-wrap"><canvas id="chartModalidade"></canvas></div>
  </div>
 
  <div class="card wide">
    <h2>Top 15 Tecnologias Mais Demandadas</h2>
    <div class="chart-wrap tall"><canvas id="chartTecnologias"></canvas></div>
  </div>
 
  <div class="card wide">
    <h2>Top 10 Localizações</h2>
    <div class="chart-wrap"><canvas id="chartLocalizacao"></canvas></div>
  </div>
 
  <div class="card">
    <h2>Vagas por Portal</h2>
    <div class="chart-wrap"><canvas id="chartOrigem"></canvas></div>
  </div>
 
  <div class="card">
    <h2>Transparência Salarial</h2>
    <div class="chart-wrap"><canvas id="chartSalarios"></canvas></div>
  </div>
 
</div>
 
<script>
const D = {dados_json};
const COLORS = {cores};
 
// ── Configuração padrão compartilhada ───────────────────────
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#334155';
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
 
const TOOLTIP = {{
  backgroundColor: '#1e293b',
  titleColor: '#e2e8f0',
  bodyColor: '#94a3b8',
  borderColor: '#334155',
  borderWidth: 1,
  padding: 10,
}};
 
// ── Funções auxiliares ───────────────────────────────────────
 
function barChart(id, labels, data, horizontal = false) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{
      labels,
      datasets: [{{
        data,
        backgroundColor: COLORS.slice(0, data.length),
        borderRadius: 6,
        borderSkipped: false,
      }}]
    }},
    options: {{
      indexAxis: horizontal ? 'y' : 'x',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{
        label: ctx => ` ${{ctx.parsed[horizontal ? 'x' : 'y']}} vagas`
      }}, ...TOOLTIP }}}},
      scales: {{
        x: {{ grid: {{ color: '#1e293b' }} }},
        y: {{ grid: {{ color: '#1e293b' }} }}
      }}
    }}
  }});
}}
 
function doughnutChart(id, labels, data) {{
  new Chart(document.getElementById(id), {{
    type: 'doughnut',
    data: {{
      labels,
      datasets: [{{
        data,
        backgroundColor: COLORS.slice(0, data.length),
        borderWidth: 2,
        borderColor: '#1e293b',
        hoverOffset: 8,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {{
        legend: {{
          position: 'right',
          labels: {{ boxWidth: 12, padding: 14 }}
        }},
        tooltip: {{ ...TOOLTIP, callbacks: {{
          label: ctx => ` ${{ctx.label}}: ${{ctx.parsed}} vagas`
        }}}}
      }}
    }}
  }});
}}
 
// ── Instancia os gráficos ────────────────────────────────────
 
barChart('chartSenioridade', D.senioridade.labels, D.senioridade.data);
barChart('chartTecnologias', D.tecnologias.labels, D.tecnologias.data, true);
barChart('chartLocalizacao', D.localizacao.labels, D.localizacao.data, true);
doughnutChart('chartModalidade', D.modalidade.labels, D.modalidade.data);
doughnutChart('chartOrigem',     D.origem.labels,     D.origem.data);
doughnutChart('chartSalarios',   D.salarios.labels,   D.salarios.data);
</script>
 
</body>
</html>"""
