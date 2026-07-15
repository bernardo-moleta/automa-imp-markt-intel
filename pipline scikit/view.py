import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def gerar_dashboard_html():
    """Converte os outputs do ML em um Dashboard HTML interativo moderno e responsivo."""
    logger.info("🎨 Iniciando construção do Dashboard Interativo...")

    # 1. Carregar dados do pipeline alinhado
    try:
        df_hist = pd.read_csv("dados_features_engenheirados.csv")
        df_prev = pd.read_csv("previsoes_futuro.csv")
        # Nome do arquivo atualizado para bater com o novo pipeline
        with open("previsoes_ml_sklearn.json", 'r', encoding='utf-8') as f:
            dados_json = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"❌ Arquivos de dados não encontrados. Execute o pipeline primeiro. Erro: {e}")
        return

    # 2. Preparar dados para o Chart.js
    df_hist['Data'] = pd.to_datetime(df_hist['Data'])
    df_prev['Data'] = pd.to_datetime(df_prev['Data'])
    
    # Concatenar as datas mantendo a ordem cronológica
    labels = pd.concat([df_hist['Data'], df_prev['Data']]).dt.strftime('%Y-%m-%d').tolist()
    
# Alinhamento das séries para o gráfico interativo (null onde não houver dado)
    # Aplicando astype(float) e float() nativo para evitar o erro de serialização do JSON
    valores_historicos = df_hist['Volume_Total'].astype(float).tolist() + [None] * len(df_prev)
    
    ultimo_valor = float(df_hist['Volume_Total'].iloc[-1])
    valores_previsao = [None] * (len(df_hist) - 1) + [ultimo_valor] + df_prev['Volume_Previsto'].astype(float).tolist()
    # 3. Extrair métricas dos modelos dinamicamente
    metricas_html = ""
    for modelo, valores in dados_json.get("metricas", {}).items():
        mape_formatado = f"{valores.get('mape', 0.0):.2%}"
        rmse_formatado = f"{valores.get('rmse', 0.0):,.2f}".replace(",", ".")
        
        metricas_html += f"""
        <div class="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
            <h3 class="text-sm font-medium text-[#8b949e] uppercase tracking-wider">{modelo}</h3>
            <div class="mt-4 flex items-baseline justify-between">
                <div>
                    <span class="text-xs text-[#8b949e]">MAPE (Erro Médio)</span>
                    <p class="text-2xl font-semibold text-[#58a6ff]">{mape_formatado}</p>
                </div>
                <div class="text-right">
                    <span class="text-xs text-[#8b949e]">RMSE</span>
                    <p class="text-lg font-medium text-[#c9d1d9]">{rmse_formatado}</p>
                </div>
            </div>
        </div>
        """

    # 4. Extrair e estruturar a Importância das Features (Top 5 do modelo campeão)
    # Descobre o melhor modelo baseado no menor MAPE
    melhor_modelo_nome = min(dados_json["metricas"].items(), key=lambda x: x[1]["mape"])[0]
    features_importantes = dados_json.get("feature_importance", {}).get(melhor_modelo_nome, {})
    
    features_html = ""
    for feat, imp in list(features_importantes.items())[:5]:
        peso_pct = f"{float(imp):.1%}"  # Convertendo para float antes de formatar
        features_html += f"""
        <div class="flex items-center justify-between py-2 border-b border-[#21262d] text-sm">
            <span class="font-mono text-[#c9d1d9]">{feat}</span>
            <span class="text-[#58a6ff] font-medium">{peso_pct}</span>
        </div>
        """

    # 5. Construção do Template HTML (Estrutura visual limpa e austera)
    html_content = f"""<!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SIACESP | Inteligência de Importação</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body class="bg-[#0d1117] text-[#e6edf3] font-sans antialiased min-h-screen pb-12">
        
        <header class="border-b border-[#30363d] bg-[#161b22] py-5 px-6 sticky top-0 z-50">
            <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                    <h1 class="text-xl font-semibold tracking-tight text-[#f0f6fc]">SIACESP - Volume de Importações</h1>
                    <p class="text-xs text-[#8b949e] mt-1">Pipeline de Engenharia de Features Estrita & Modelos Preditivos</p>
                </div>
                <div class="text-xs text-[#8b949e] bg-[#21262d] px-3 py-1.5 rounded-md border border-[#30363d]">
                    Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-4 md:px-6 mt-8 space-y-6">
            
            <section class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {metricas_html}
            </section>

            <section class="grid grid-cols-1 lg:grid-cols-4 gap-6">
                
                <div class="lg:col-span-3 bg-[#161b22] border border-[#30363d] rounded-lg p-5 flex flex-col justify-between">
                    <div class="mb-4">
                        <h2 class="text-base font-medium text-[#f0f6fc]">Previsão do Volume para os Próximos Meses</h2>
                        <p class="text-xs text-[#8b949e]">Horizonte projetado de curto prazo sem data leakage</p>
                    </div>
                    <div class="relative w-full h-[400px]">
                        <canvas id="chartPrevisao"></canvas>
                    </div>
                </div>

                <div class="space-y-4">
                    <div class="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
                        <h2 class="text-sm font-medium text-[#f0f6fc] mb-1">Drivers Preditivos</h2>
                        <p class="text-xs text-[#8b949e] mb-4">Top 5 features de maior peso ({melhor_modelo_nome})</p>
                        <div class="divide-y divide-[#21262d]">
                            {features_html}
                        </div>
                    </div>

                    <div class="bg-[#161b22] border border-[#30363d] rounded-lg p-5 text-xs text-[#8b949e] space-y-2">
                        <p class="font-medium text-[#c9d1d9]">Configuração do Modelo:</p>
                        <p>• Lags Calculados: 1, 2 e 12 meses (restrito)</p>
                        <p>• Médias Móveis: Janelas de 3, 6 e 12 meses</p>
                        <p>• Macro Drivers: Câmbio (USD_BRL) e ENSO</p>
                        <p>• Codificação Sazonal: Seno/Cosseno Cíclico</p>
                    </div>
                </div>
            </section>
        </main>

        <script>
            const ctx = document.getElementById('chartPrevisao').getContext('2d');
            
            const labelsData = {json.dumps(labels)};
            const dadosHistoricos = {json.dumps(valores_historicos)};
            const dadosPrevisao = {json.dumps(valores_previsao)};

            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labelsData,
                    datasets: [
                        {{
                            label: 'Volume Histórico',
                            data: dadosHistoricos,
                            borderColor: '#8b949e',
                            borderWidth: 2,
                            backgroundColor: 'transparent',
                            pointRadius: 1,
                            tension: 0.1
                        }},
                        {{
                            label: 'Projeção do Modelo',
                            data: dadosPrevisao,
                            borderColor: '#58a6ff',
                            borderWidth: 2.5,
                            borderDash: [5, 5],
                            backgroundColor: 'rgba(88, 166, 255, 0.05)',
                            fill: true,
                            pointRadius: 3,
                            pointBackgroundColor: '#58a6ff',
                            tension: 0.1
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{
                            position: 'top',
                            labels: {{ color: '#c9d1d9', font: {{ size: 12 }} }}
                        }},
                        tooltip: {{
                            backgroundColor: '#161b22',
                            titleColor: '#58a6ff',
                            bodyColor: '#e6edf3',
                            borderColor: '#30363d',
                            borderWidth: 1,
                            padding: 10,
                            callbacks: {{
                                label: function(context) {{
                                    let label = context.dataset.label || '';
                                    if (label) label += ': ';
                                    if (context.raw !== null) {{
                                        label += Number(context.raw).toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }}) + ' t';
                                    }}
                                    return label;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ 
                            grid: {{ color: '#21262d' }}, 
                            ticks: {{ color: '#8b949e', maxTicksLimit: 12 }} 
                        }},
                        y: {{ 
                            grid: {{ color: '#21262d' }}, 
                            ticks: {{ 
                                color: '#8b949e',
                                callback: (v) => v.toLocaleString('pt-BR') + ' t'
                            }} 
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    # Gravação do arquivo final refinado
    with open("dashboard_previsao_interativo.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info("✅ Dashboard gerado com sucesso: dashboard_previsao_interativo.html")

if __name__ == "__main__":
    gerar_dashboard_html()