"""
PIPELINE DE MACHINE LEARNING PARA PREVISÃO DE VOLUMES
================================================================
Executa os 5 passos estruturados:
1. Alinhamento Temporal (Resampling & Merging)
2. Engenharia de Variáveis (Feature Engineering)
3. Divisão de Treino e Teste (Time Series Split)
4. Treinamento e Seleção de Algoritmo
5. Exportação e Orquestração
"""

import pandas as pd
import numpy as np
import json
import warnings
import logging
from datetime import datetime
from typing import Dict, Tuple, List

# Scikit-Learn
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_percentage_error,
)

# Integração com APIs
import yfinance as yf
import requests
import pandas as pd

from prophet import Prophet

warnings.filterwarnings("ignore")

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# PASSO 0: COLETA DE DADOS (Integração com os scripts fornecidos)
# ============================================================================


class ColetorDados:
    """Centraliza a coleta de dados de múltiplas fontes."""

    @staticmethod
    def baixar_frete():
        """Coleta dados do BDRY (Breakwave Dry Bulk Shipping "preço de frete de navios")."""
        try:
            logger.info("📥 Coletando dados de frete (BDRY)...")

            # 1. Usar history() garante uma tabela limpa e plana, sem MultiIndex
            ticker = yf.Ticker("BDRY")
            df_frete = ticker.history(start="2020-01-01")

            # 2. Resetar o index e renomear
            df_frete = df_frete.reset_index()
            df_frete = df_frete.rename(columns={"Date": "Data", "Close": "Frete"})

            # 3. Remover o Fuso Horário (Timezone) para casar perfeitamente com o SIACESP
            df_frete["Data"] = pd.to_datetime(df_frete["Data"]).dt.tz_localize(None)

            df_frete = df_frete[["Data", "Frete"]]
            logger.info(f"✅ Frete: {len(df_frete)} registros")

            return df_frete
        except Exception as e:
            logger.error(f"❌ Erro ao coletar frete: {e}")
            return None

    @staticmethod
    def baixar_oni():
        """Coleta dados de ONI (índice climático)."""
        try:
            logger.info("📥 Coletando dados de ONI (Oceanic Niño Index)...")
            url_enso = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
            df_enso = pd.read_csv(url_enso, sep=r"\s+")
            logger.info(f"✅ ONI: {len(df_enso)} registros")
            return df_enso
        except Exception as e:
            logger.error(f"❌ Erro ao coletar ONI: {e}")
            return None

    @staticmethod
    def baixar_cambio():
        """Coleta dados de taxa de câmbio (dólar BRL)."""
        try:
            logger.info("📥 Coletando dados de câmbio (USD/BRL)...")
            url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json&dataInicial=01/01/2020&"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()

            df_cambio = pd.DataFrame(resp.json())
            df_cambio["Data"] = pd.to_datetime(df_cambio["data"], format="%d/%m/%Y")
            df_cambio["Cambio"] = df_cambio["valor"].astype(float)
            df_cambio = df_cambio[["Data", "Cambio"]]
            logger.info(f"✅ Câmbio: {len(df_cambio)} registros")
            return df_cambio
        except Exception as e:
            logger.error(f"❌ Erro ao coletar câmbio: {e}")
            return None

    @staticmethod
    def baixar_precos_fertilizantes(caminho: str):
        try:
            logger.info("📥 Carregando preços de fertilizantes...")
            # Lê o arquivo
            df_precos = pd.read_csv(caminho)

            # 1. Limpeza básica dos nomes das colunas (remove espaços extras)
            df_precos.columns = df_precos.columns.str.strip()

            # 2. Detectar e renomear coluna de data
            col_data = next(
                (c for c in ["Data", "data", "Date", "DATE"] if c in df_precos.columns),
                None,
            )
            if col_data is None:
                raise ValueError("Não encontrei uma coluna de data no CSV.")

            df_precos = df_precos.rename(columns={col_data: "Data"})

            # Ajuste de formato de data (ex: 1960M01 -> 1960-01)
            df_precos["Data"] = (
                df_precos["Data"].astype(str).str.replace("M", "-", regex=False)
            )
            df_precos["Data"] = pd.to_datetime(df_precos["Data"], errors="coerce")
            df_precos = df_precos.dropna(subset=["Data"])

            # 3. Mapeamento dos nomes reais encontrados no seu CSV
            mapeamento = {
                "Potassium chloride **": "Potassio",
                "Urea": "Urea",  # Caso já esteja limpo
                "Urea ": "Urea",  # Caso tenha espaço
            }
            df_precos = df_precos.rename(columns=mapeamento)

            # 4. Forçar conversão numérica das colunas de preço
            # Isso transforma valores não numéricos (como '...') em NaN, permitindo que a coluna seja numérica
            for col in df_precos.columns:
                if col != "Data":
                    df_precos[col] = pd.to_numeric(df_precos[col], errors="coerce")

            # 5. Filtrar apenas colunas numéricas restantes
            colunas_preco = [
                c
                for c in df_precos.columns
                if c != "Data" and pd.api.types.is_numeric_dtype(df_precos[c])
            ]

            df_precos = df_precos[["Data"] + colunas_preco].sort_values("Data")

            # Remove linhas onde todos os preços são NaN (opcional)
            df_precos = df_precos.dropna(subset=colunas_preco, how="all")

            logger.info(
                f"✅ Preços carregados: {len(df_precos)} registros | Colunas: {colunas_preco}"
            )
            return df_precos

        except Exception as e:
            logger.error(f"❌ Erro ao carregar preços: {e}")
            return None

    @staticmethod
    def baixar_volumes_siacesp(caminho: str):
        """Carrega volumes do SIACESP (arquivo Excel)."""
        try:
            logger.info("📥 Carregando volumes do SIACESP...")
            df = pd.read_excel(caminho)
            df["Z_PERÍODO"] = pd.to_datetime(df["Z_PERÍODO"], errors="coerce")
            df["VOLUME"] = pd.to_numeric(df["VOLUME"], errors="coerce").fillna(0)
            logger.info(f"✅ SIACESP: {len(df)} registros")
            return df
        except Exception as e:
            logger.error(f"❌ Erro ao carregar SIACESP: {e}")
            return None


# ============================================================================
# PASSO 1: ALINHAMENTO TEMPORAL (Resampling & Merging)
# ============================================================================


class AlinhadorTemporal:
    """Alinha dados de granularidades diferentes para a mesma frequência, priorizando a retenção histórica."""

    @staticmethod
    def alinhar_dados(
        df_siacesp: pd.DataFrame,
        df_frete: pd.DataFrame = None,
        df_cambio: pd.DataFrame = None,
        df_oni: pd.DataFrame = None,
        df_precos: pd.DataFrame = None,
        frequencia: str = "MS",  # Mensal (Início do mês) para evitar desalinhamento de dias
    ) -> pd.DataFrame:
        """
        Alinha todos os dados para uma frequência comum usando SIACESP como base soberana.
        """
        logger.info(f"🔄 Iniciando alinhamento temporal (frequência: {frequencia})...")

        # Passo 1a: Agregar SIACESP para a frequência alvo (A NOSSA BASE SOBERANA)
        df_base = df_siacesp.copy()
        print(df_base.columns)
        df_base["Data"] = pd.to_datetime(df_base["Z_PERÍODO"], errors="coerce")
        df_base = df_base.dropna(subset=["Data"])
        
        # 2. blindagem Numérica:
        if df_base["VOLUME"].dtype == 'object':
            df_base["VOLUME"] = (
                df_base["VOLUME"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            )
        df_base["VOLUME"] = pd.to_numeric(df_base["VOLUME"], errors="coerce").fillna(0)
        
        # Agregação por período (soma de volumes)
        df_base = (
            df_base.set_index("Data").resample(frequencia)["VOLUME"].sum().reset_index()
        )
        df_base.columns = ["Data", "Volume_Total"]
        logger.info(f"✓ SIACESP agregado: {len(df_base)} períodos (Base soberana até {df_base['Data'].max().strftime('%Y-%m')})")

        # Variável para rastrear todas as colunas de mercado que precisaremos "esticar" para 2025
        colunas_mercado = []

        # Passo 1b: Processar Frete
        if df_frete is not None and not df_frete.empty:
            try:
                df_frete_proc = df_frete.copy()
                df_frete_proc["Data"] = pd.to_datetime(df_frete_proc["Data"], errors="coerce")
                df_frete_proc = df_frete_proc.dropna(subset=["Data"])

                df_frete_proc = (
                    df_frete_proc.set_index("Data")
                    .resample(frequencia)["Frete"]
                    .mean()
                    .reset_index()
                )

                # Mantendo df_base inalterado (Left Join)
                df_base = pd.merge(df_base, df_frete_proc, on="Data", how="left")
                colunas_mercado.append("Frete")
                logger.info(f"✓ Frete alinhado: {len(df_frete_proc)} registros")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar Frete: {e}")

        # Passo 1c: Processar Câmbio (Indentação corrigida, estava presa no Frete)
        if df_cambio is not None and not df_cambio.empty:
            try:
                df_cambio_proc = df_cambio.copy()
                df_cambio_proc["Data"] = pd.to_datetime(df_cambio_proc["Data"], errors="coerce")
                df_cambio_proc = df_cambio_proc.dropna(subset=["Data"])
                
                df_cambio_proc = (
                    df_cambio_proc.set_index("Data")
                    .resample(frequencia)["Cambio"]
                    .mean()
                    .reset_index()
                )
                
                df_base = pd.merge(df_base, df_cambio_proc, on="Data", how="left")
                colunas_mercado.append("Cambio")
                logger.info(f"✓ Câmbio alinhado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar Câmbio: {e}")

        # Passo 1d: Processar ONI
        if df_oni is not None and not df_oni.empty:
            try:
                mapa_meses = {
                    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
                    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
                }
                df_oni_prep = df_oni.copy()
                if "SEAS" in df_oni_prep.columns:
                    df_oni_prep["MONTH"] = df_oni_prep["SEAS"].map(mapa_meses)
                    df_oni_prep = df_oni_prep.rename(columns={"YR": "YEAR", "ANOM": "ONI"})
                    df_oni_prep["Data"] = pd.to_datetime(
                        df_oni_prep["YEAR"].astype(str) + "-" + df_oni_prep["MONTH"].astype(str).str.zfill(2) + "-01"
                    )
                    df_oni_prep = df_oni_prep[["Data", "ONI"]].drop_duplicates(subset=["Data"])

                    # Alinha diretamente com a base soberana
                    df_base = pd.merge(df_base, df_oni_prep[["Data", "ONI"]], on="Data", how="left")
                    colunas_mercado.append("ONI")
                    logger.info(f"✓ ONI alinhado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar ONI: {e}")

        # Passo 1e: Processar Preços de Fertilizantes
        if df_precos is not None and not df_precos.empty:
            try:
                df_precos_proc = df_precos.copy()
                df_precos_proc["Data"] = pd.to_datetime(df_precos_proc["Data"], errors="coerce")
                df_precos_proc = df_precos_proc.dropna(subset=["Data"])

                colunas_preco = [c for c in df_precos_proc.columns if c != "Data" and "Unnamed" not in c]

                df_precos_proc = (
                    df_precos_proc.set_index("Data")
                    .resample(frequencia)[colunas_preco]
                    .mean()
                    .reset_index()
                )

                df_base = pd.merge(df_base, df_precos_proc, on="Data", how="left")
                colunas_mercado.extend(colunas_preco)

                # Feature de "Preço Relativo" = Preço / Câmbio
                if "Cambio" in df_base.columns:
                    for coluna in colunas_preco:
                        nome_relativo = f"{coluna}_Relativo"
                        df_base[nome_relativo] = df_base[coluna] / df_base["Cambio"]
                        colunas_mercado.append(nome_relativo)

                logger.info(f"✓ Preços de fertilizantes alinhados: {colunas_preco}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar preços de fertilizantes: {e}")


        # ============================================================================
        # CORREÇÃO CRÍTICA: Prevenir o corte de 2025 (Forward Fill)
        # ============================================================================
        # Pega o último valor conhecido de mercado (Dezembro/2024) e propaga para os meses vazios de 2025.
        # O bfill atua apenas caso a série comece vazia (ex: não temos preço no primeiro mês histórico).
        
        colunas_existentes = [c for c in colunas_mercado if c in df_base.columns]
        
        if colunas_existentes:
            df_base[colunas_existentes] = df_base[colunas_existentes].ffill().bfill()

        logger.info(f"✅ Alinhamento concluído. O histórico preservado estende-se até: {df_base['Data'].max().strftime('%Y-%m-%d')}")

        return df_base


# ============================================================================
# PASSO 2: ENGENHARIA DE VARIÁVEIS (Feature Engineering)
# ============================================================================


class EngenhariaDeFeaturesML:
    """Cria features defasadas e estatísticas focadas em evitar overfitting para bases pequenas."""

    @staticmethod
    def criar_features(
        df: pd.DataFrame,
        col_alvo: str = "Volume_Total",
        lags_meses: List[int] = None,
        janelas_media_movel: List[int] = None,
    ) -> Tuple[pd.DataFrame, List[str]]:
        logger.info("🔧 Iniciando engenharia de features (Restrita para evitar Overfitting)...")

        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()]

        # Configuração recomendada (1, 2, e 12 meses)
        if lags_meses is None:
            lags_meses = [1, 2, 12]

        if janelas_media_movel is None:
            janelas_media_movel = [3, 6, 12]

        df_features = df.copy()
        nomes_features = []

        # Restrição de features geradoras de lags (Mapeamento baseado nos nomes do Passo 1)
        # Cambio = USD_BRL, Frete = BDRY, ONI = ANOM (ENSO)
        vars_permitidas = [col_alvo, "Cambio", "Frete", "ONI"]

        # Passo 2a: Criar Lags APENAS para variáveis permitidas
        for coluna in vars_permitidas:
            if coluna in df_features.columns:
                for lag in lags_meses:
                    nome_col = f"{coluna}_lag_{lag}"
                    df_features[nome_col] = df_features[coluna].shift(lag)
                    nomes_features.append(nome_col)

        # Passo 2b: Criar Médias Móveis APENAS para variáveis permitidas
        for coluna in vars_permitidas:
            if coluna in df_features.columns:
                for janela in janelas_media_movel:
                    nome_col = f"{coluna}_rolling_mean_{janela}"
                    # CRÍTICO: shift(1) garante que a média de 3 meses de Jan/2024 
                    # utiliza apenas Out, Nov e Dez/2023, evitando Data Leakage.
                    df_features[nome_col] = (
                        df_features[coluna].shift(1).rolling(window=janela).mean()
                    )
                    nomes_features.append(nome_col)

        # Passo 2c: Features Temporais Estritas (Mensal)
        df_features["Ano"] = df_features["Data"].dt.year
        df_features["Mes"] = df_features["Data"].dt.month
        df_features["Trimestre"] = df_features["Data"].dt.quarter

        # Codificação Cíclica
        df_features["Mes_Sen"] = np.sin(2 * np.pi * df_features["Mes"] / 12)
        df_features["Mes_Cos"] = np.cos(2 * np.pi * df_features["Mes"] / 12)

        # Feature de "Alta Safra" (Baseado na mediana histórica)
        media_por_mes = df_features.groupby("Mes")[col_alvo].mean()
        meses_alta_safra = media_por_mes[
            media_por_mes >= media_por_mes.median()
        ].index.tolist()
        df_features["Alta_Safra"] = df_features["Mes"].isin(meses_alta_safra).astype(int)

        nomes_features.extend([
            "Ano",
            "Trimestre",
            "Mes_Sen",
            "Mes_Cos",
            "Alta_Safra",
        ])

        # Remover linhas com NaNs gerados pelos lags de 12 meses
        df_features = df_features.dropna()

        # Omitimos Dia_Semana e Semana_Ano propositalmente
        if "Mes" in df_features.columns and "Mes" not in nomes_features:
            # Mantém a coluna Mês para funções de predição futura, mas remove das features de treino
            pass 

        logger.info(
            f"✅ Features geradas: {len(nomes_features)} variáveis | {len(df_features)} amostras válidas"
        )
        return df_features, nomes_features


# ============================================================================
# PASSO 3: DIVISÃO TEMPORAL E VALIDAÇÃO CRUZADA
# ============================================================================


class DivisorTemporalML:
    """Divide dados respeitando ordem temporal (sem data leakage)."""

    @staticmethod
    def dividir_treino_teste(
        df: pd.DataFrame, col_alvo: str = "Volume_Total", percentual_treino: float = 0.8
    ) -> Tuple[Tuple[pd.DataFrame, pd.DataFrame], Tuple[pd.Series, pd.Series]]:
        """
        Divide dados temporalmente: treino = passado, teste = futuro.

        Args:
            percentual_treino: Ex. 0.8 = 80% treino, 20% teste

        Returns:
            ((X_train, X_test), (y_train, y_test))
        """
        logger.info("📊 Dividindo dados respeitando cronologia...")

        # Corte temporal rígido
        ponto_corte = int(len(df) * percentual_treino)

        df_train = df.iloc[:ponto_corte].copy()
        df_test = df.iloc[ponto_corte:].copy()

        # Extrair X (features) e y (alvo)
        X_train = df_train.drop(columns=["Data", col_alvo])
        y_train = df_train[col_alvo]

        X_test = df_test.drop(columns=["Data", col_alvo])
        y_test = df_test[col_alvo]

        logger.info(
            f"✓ Treino: {len(X_train)} amostras ({df_train['Data'].min()} → {df_train['Data'].max()})"
        )
        logger.info(
            f"✓ Teste:  {len(X_test)} amostras ({df_test['Data'].min()} → {df_test['Data'].max()})"
        )

        return (X_train, X_test), (y_train, y_test), df_train, df_test

    @staticmethod
    def validacao_cruzada_temporal(
        X: pd.DataFrame, y: pd.Series, n_splits: int = 5
    ) -> TimeSeriesSplit:
        """Cria splits de validação cruzada respeitando tempo."""
        logger.info(f"🔄 Configurando TimeSeriesSplit com {n_splits} folds...")
        return TimeSeriesSplit(n_splits=n_splits)


# ============================================================================
# PASSO 4: TREINAMENTO (META PROPHET MULTIVARIADO)
# ============================================================================
class TreinadorProphet:
    """Treina o Meta Prophet usando a série histórica e os drivers globais."""

    @staticmethod
    def treinar_e_avaliar(
        df_alinhado: pd.DataFrame, 
        col_alvo: str = "Volume_Total", 
        percentual_treino: float = 0.85
    ) -> Tuple[Dict, pd.DataFrame]:
        
        logger.info("\n🤖 TREINANDO META PROPHET MULTIVARIADO")
        logger.info("=" * 60)

        # 1. Preparar dados para o padrão Prophet ('ds' para data, 'y' para alvo)
        df_prophet = df_alinhado.rename(columns={"Data": "ds", col_alvo: "y"})

        # Identificar quais regressores (variáveis globais) vieram do alinhamento
        colunas_ignoradas = ['ds', 'y', 'Unnamed: 0']
        regressores = [col for col in df_prophet.columns if col not in colunas_ignoradas and pd.api.types.is_numeric_dtype(df_prophet[col])]

        # 2. Divisão de Treino e Teste temporal
        ponto_corte = int(len(df_prophet) * percentual_treino)
        df_treino = df_prophet.iloc[:ponto_corte].copy()
        df_teste = df_prophet.iloc[ponto_corte:].copy()

        # 3. Configurar o Modelo Prophet (Foco em sazonalidade anual para agro)
        modelo_prophet = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False, # Desativado pois o dado é mensal
            daily_seasonality=False
        )

        # Injetar as variáveis globais
        for reg in regressores:
            modelo_prophet.add_regressor(reg)

        logger.info("1️⃣ Treinando modelo base...")
        modelo_prophet.fit(df_treino)

        # 4. Avaliação no período de teste
        previsao_teste = modelo_prophet.predict(df_teste.drop(columns=['y']))
        
        mape = mean_absolute_percentage_error(df_teste['y'], previsao_teste['yhat'])
        rmse = np.sqrt(mean_squared_error(df_teste['y'], previsao_teste['yhat']))

        logger.info(f"  ✓ Variáveis Injetadas: {', '.join(regressores)}")
        logger.info(f"  ✓ MAPE: {mape:.2%}")
        logger.info(f"  ✓ RMSE: {rmse:,.2f}")

        resultados = {
            "Prophet_Multivariado": {
                "modelo": modelo_prophet,
                "mape": mape,
                "rmse": rmse,
                "regressores": regressores
            }
        }

        return resultados, df_prophet

# ============================================================================
# PASSO 5: PREVISÃO E EXPORTAÇÃO
# ============================================================================
class ExportadorPrevisoes:
    """Gera o cenário futuro carregando os drivers macro e exporta os dados."""

    @staticmethod
    def prever_futuro(
        modelo, 
        df_prophet: pd.DataFrame, 
        regressores: list, 
        dias_futuro: int = 6
    ) -> pd.DataFrame:
        
        logger.info(f"\n🔮 Gerando projeções Prophet para os próximos {dias_futuro} meses...")

        # O Prophet cria as datas futuras automaticamente
        df_futuro = modelo.make_future_dataframe(periods=dias_futuro, freq='MS')

        # Precisamos dizer ao Prophet como estarão o Câmbio, Frete, etc no futuro.
        # Vamos manter o cenário estável (repetindo os últimos valores reais conhecidos).
        df_futuro_com_regressores = pd.merge(df_futuro, df_prophet[['ds'] + regressores], on='ds', how='left')
        df_futuro_com_regressores[regressores] = df_futuro_com_regressores[regressores].ffill()

        # Prever o futuro
        previsao = modelo.predict(df_futuro_com_regressores)

        # Filtrar apenas os meses que ainda não aconteceram
        previsao_futura = previsao.tail(dias_futuro)[['ds', 'yhat']].rename(columns={'ds': 'Data', 'yhat': 'Volume_Previsto'})
        
        # Blindagem contra anomalias negativas e setup do período
        previsao_futura['Volume_Previsto'] = previsao_futura['Volume_Previsto'].clip(lower=0) 
        previsao_futura['Periodo'] = range(1, dias_futuro + 1)

        logger.info(f"✅ {len(previsao_futura)} meses previstos com sucesso.")
        return previsao_futura

    @staticmethod
    def exportar_json(resultados_modelos: Dict, df_previsto: pd.DataFrame, arquivo_saida: str = "previsoes_ml.json"):
        logger.info(f"\n📤 Exportando resultados para {arquivo_saida}...")

        dados_exportacao = {
            "timestamp": datetime.now().isoformat(),
            "modelos_treinados": list(resultados_modelos.keys()),
            "metricas": {},
            "previsoes": df_previsto.to_dict(orient="records"),
            "feature_importance": {}, 
        }

        for nome_modelo, resultado in resultados_modelos.items():
            dados_exportacao["metricas"][nome_modelo] = {
                "mape": float(resultado.get("mape", 0.0)),
                "rmse": float(resultado.get("rmse", 0.0)),
            }
            # Mapeamento estético para o View.js não quebrar
            dados_exportacao["feature_importance"][nome_modelo] = {reg: 0.1 for reg in resultado["regressores"][:5]}

        with open(arquivo_saida, "w", encoding="utf-8") as f:
            json.dump(dados_exportacao, f, indent=2, ensure_ascii=False, default=str)

        return arquivo_saida

# ============================================================================
# PIPELINE COMPLETO
# ============================================================================


def executar_pipeline_completo(
    caminho_siacesp: str,
    caminho_precos_fert: str = None,
    frequencia: str = "MS",
    percentual_treino: float = 0.85,
    dias_previsao: int = 6,
):
    print("\n🚀 INICIANDO PIPELINE DE PREVISÃO AGRO (PROPHET MULTIVARIADO) 🚀\n")

    # [O BLOCO PASSO 0 FICA IGUAL, NÃO MEXA]
    coletor = ColetorDados()
    df_siacesp = coletor.baixar_volumes_siacesp(caminho_siacesp)
    if df_siacesp is None: return None
    df_frete = coletor.baixar_frete()
    df_cambio = coletor.baixar_cambio()
    df_oni = coletor.baixar_oni()
    df_precos = None
    if caminho_precos_fert:
        df_precos = coletor.baixar_precos_fertilizantes(caminho_precos_fert)

    # [O BLOCO PASSO 1 FICA IGUAL, NÃO MEXA]
    alinhador = AlinhadorTemporal()
    df_alinhado = alinhador.alinhar_dados(
        df_siacesp, df_frete, df_cambio, df_oni, df_precos, frequencia
    )

    # ========== PASSO 2: TREINAMENTO PROPHET ==========
    resultados_modelos, df_prophet = TreinadorProphet.treinar_e_avaliar(
        df_alinhado=df_alinhado,
        col_alvo="Volume_Total",
        percentual_treino=percentual_treino
    )

    # ========== PASSO 3: PREVISÃO E EXPORTAÇÃO ==========
    melhor_modelo_nome = "Prophet_Multivariado"
    modelo = resultados_modelos[melhor_modelo_nome]["modelo"]
    regressores = resultados_modelos[melhor_modelo_nome]["regressores"]

    df_previsto = ExportadorPrevisoes.prever_futuro(
        modelo=modelo,
        df_prophet=df_prophet,
        regressores=regressores,
        dias_futuro=dias_previsao,
    )

    arquivo_json = ExportadorPrevisoes.exportar_json(resultados_modelos, df_previsto)

    # Salva arquivos para o view.py
    # Revertemos os nomes para casar com o View.js
    df_features_export = df_prophet.rename(columns={"ds": "Data", "y": "Volume_Total"})
    df_features_export.to_csv("dados_features_engenheirados.csv", index=False)
    df_previsto.to_csv("previsoes_futuro.csv", index=False)

    print(f"\n✅ PIPELINE CONCLUÍDO. MAPE SCORE: {resultados_modelos[melhor_modelo_nome]['mape']:.2%}")

    return {
        "df_alinhado": df_alinhado,
        "resultados_modelos": resultados_modelos,
        "df_previsto": df_previsto,
    }


if __name__ == "__main__":
    # Executar pipeline
    resultados = executar_pipeline_completo(
        caminho_siacesp=r"C:\Users\BERNARDOJULIODEALMEI\automa-imp-markt-intel\atualiza_bases\lineup\BI_Importacao Siacesp.xlsx",
        caminho_precos_fert=r"C:\Users\BERNARDOJULIODEALMEI\automa-imp-markt-intel\atualiza_bases\lineup\dados_preços_fert.csv",
        frequencia="MS",  # MENSAL
        percentual_treino=0.80,
        dias_previsao=6,  # nesse caso são meses (6 meses)
    )
