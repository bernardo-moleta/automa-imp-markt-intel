import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def gerar_dashboard_html():
    """Converte os outputs do ML em um Dashboard HTML interativo estilo Prophet."""
    logger.info("🎨 Iniciando construção do Dashboard Interativo...")

    # 1. Carregar dados do pipeline
    try:
        df_hist = pd.read_csv("dados_features_engenheirados.csv")
        df_prev = pd.read_csv("previsoes_futuro.csv")
        with open("previsoes_ml_sklearn.json", 'r') as f:
            dados_json = json.load(f)
    except FileNotFoundError:
        logger.error("❌ Arquivos de dados não encontrados. Execute o pipeline primeiro.")
        return

   # 2. Preparar dados para o Chart.js
    # Precisamos garantir que as datas estejam em ordem e concatenadas
    df_hist['Data'] = pd.to_datetime(df_hist['Data'])
    df_prev['Data'] = pd.to_datetime(df_prev['Data'])
    
    # Criamos as listas de dados. Onde for histórico, a previsão é null e vice-versa
    labels = pd.concat([df_hist['Data'], df_prev['Data']]).dt.strftime('%Y-%m-%d').tolist()
    
    # Extrair e converter o último valor para float nativo do Python (Evita o TypeError)
    ultimo_real = float(df_hist['Volume_Total'].iloc[-1])
    
    # Volume Real (Histórico) - Usar astype(float) elimina os numpy.int64
    real = df_hist['Volume_Total'].astype(float).tolist() + [None] * len(df_prev)
    
    # Volume Projetado (ML) - Começa com o último valor real para conectar as linhas
    proj = [None] * (len(df_hist) - 1) + [ultimo_real] + df_prev['Volume_Previsto'].astype(float).tolist()
    
    # Intervalo de Confiança (Simulado 15% para estética Prophet)
    upper = [None] * (len(df_hist) - 1) + [ultimo_real] + (df_prev['Volume_Previsto'] * 1.15).astype(float).tolist()
    lower = [None] * (len(df_hist) - 1) + [ultimo_real] + (df_prev['Volume_Previsto'] * 0.85).astype(float).tolist()
    # 3. Template HTML com CSS e JS embutidos
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Previsão de Volume ML - Dashboard</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
            :root {{
                --bg: #0d1117; --surface: #161b22; --border: #30363d;
                --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff; --warn: #d29922;
            }}
            body {{ background: var(--bg); color: var(--text); font-family: 'IBM Plex Sans', sans-serif; margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 20px; }}
            .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }}
            .kpi-card {{ background: #1c2128; border: 1px solid var(--border); padding: 15px; border-radius: 6px; text-align: center; }}
            .kpi-value {{ font-family: 'IBM Plex Mono', monospace; font-size: 24px; color: var(--accent); font-weight: bold; }}
            .kpi-label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; }}
            h2, h3 {{ margin: 0; }}
            .chart-wrapper {{ height: 500px; position: relative; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h2>Projeção de Volume Importação</h2>
                    <p style="color: var(--muted); margin: 5px 0 0 0;">Pipeline ML: RandomForestRegressor + Alinhamento SIACESP</p>
                </div>
                <div style="text-align: right">
                    <span style="font-family: 'IBM Plex Mono'; font-size: 12px; color: var(--muted);">Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
                </div>
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">Média Histórica</div>
                    <div class="kpi-value">{df_hist['Volume_Total'].mean():,.0f} t</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Projeção Próximo Pico</div>
                    <div class="kpi-value">{df_prev['Volume_Previsto'].max():,.0f} t</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Acurácia R² (Treino)</div>
                    <div class="kpi-value">{dados_json['metricas']['RandomForest']['r2']:.2%}</div>
                </div>
            </div>

            <div class="card">
                <h3>Gráfico de Tendência (Prophet Style)</h3>
                <div class="chart-wrapper">
                    <canvas id="mainChart"></canvas>
                </div>
            </div>
        </div>

        <script>
            const ctx = document.getElementById('mainChart').getContext('2d');
            
            const data = {{
                labels: {json.dumps(labels)},
                datasets: [
                    {{
                        label: 'Volume Real (Histórico)',
                        data: {json.dumps(real)},
                        borderColor: '#58a6ff',
                        backgroundColor: '#58a6ff',
                        borderWidth: 2,
                        pointRadius: 2,
                        tension: 0.3
                    }},
                    {{
                        label: 'Projeção ML (Futuro)',
                        data: {json.dumps(proj)},
                        borderColor: '#d29922',
                        borderDash: [5, 5],
                        borderWidth: 3,
                        pointRadius: 4,
                        tension: 0.3,
                        fill: false
                    }},
                    {{
                        label: 'Limite Superior',
                        data: {json.dumps(upper)},
                        borderColor: 'transparent',
                        pointRadius: 0,
                        fill: false,
                        tension: 0.3
                    }},
                    {{
                        label: 'Intervalo de Confiança',
                        data: {json.dumps(lower)},
                        borderColor: 'transparent',
                        backgroundColor: 'rgba(210, 153, 34, 0.15)',
                        pointRadius: 0,
                        fill: '-1', // Preenche até o dataset anterior (upper)
                        tension: 0.3
                    }}
                ]
            }};

            new Chart(ctx, {{
                type: 'line',
                data: data,
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{
                            labels: {{ 
                                color: '#e6edf3',
                                filter: (item) => !item.text.includes('Limite') 
                            }}
                        }},
                        tooltip: {{
                            backgroundColor: '#161b22',
                            titleColor: '#58a6ff',
                            borderColor: '#30363d',
                            borderWidth: 1
                        }}
                    }},
                    scales: {{
                        x: {{ grid: {{ color: '#21262d' }}, ticks: {{ color: '#8b949e' }} }},
                        y: {{ 
                            grid: {{ color: '#21262d' }}, 
                            ticks: {{ 
                                color: '#8b949e',
                                callback: (v) => v.toLocaleString() + ' t'
                            }} 
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    # Salvar o arquivo
    with open("dashboard_previsao_interativo.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info("✅ Dashboard Interativo gerado: dashboard_previsao_interativo.html")

if __name__ == "__main__":
    gerar_dashboard_html()