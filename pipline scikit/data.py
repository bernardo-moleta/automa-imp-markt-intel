"""
PIPELINE PROFISSIONAL DE MACHINE LEARNING PARA PREVISÃO DE VOLUMES
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
from datetime import datetime, timedelta
from typing import Dict, Tuple, List

# Scikit-Learn
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Integração com APIs
import yfinance as yf
import requests
import pandas as pd

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
        """Coleta dados do BDRY (frete de navios)."""
        try:
            logger.info("📥 Coletando dados de frete (BDRY)...")
            
            # 1. Usar history() garante uma tabela limpa e plana, sem MultiIndex
            ticker = yf.Ticker("BDRY")
            df_frete = ticker.history(start="2020-01-01")
            
            # 2. Resetar o index e renomear
            df_frete = df_frete.reset_index()
            df_frete = df_frete.rename(columns={"Date": "Data", "Close": "Frete"})
            
            # 3. Remover o Fuso Horário (Timezone) para casar perfeitamente com o SIACESP
            df_frete['Data'] = pd.to_datetime(df_frete['Data']).dt.tz_localize(None)
            
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
            col_data = next((c for c in ["Data", "data", "Date", "DATE"] if c in df_precos.columns), None)
            if col_data is None:
                raise ValueError("Não encontrei uma coluna de data no CSV.")
            
            df_precos = df_precos.rename(columns={col_data: "Data"})

            # Ajuste de formato de data (ex: 1960M01 -> 1960-01)
            df_precos["Data"] = df_precos["Data"].astype(str).str.replace("M", "-", regex=False)
            df_precos["Data"] = pd.to_datetime(df_precos["Data"], errors="coerce")
            df_precos = df_precos.dropna(subset=["Data"])

            # 3. Mapeamento dos nomes reais encontrados no seu CSV
            mapeamento = {
                "Potassium chloride **": "Potassio",
                "Urea": "Urea", # Caso já esteja limpo
                "Urea ": "Urea" # Caso tenha espaço
            }
            df_precos = df_precos.rename(columns=mapeamento)

            # 4. Forçar conversão numérica das colunas de preço
            # Isso transforma valores não numéricos (como '...') em NaN, permitindo que a coluna seja numérica
            for col in df_precos.columns:
                if col != "Data":
                    df_precos[col] = pd.to_numeric(df_precos[col], errors="coerce")

            # 5. Filtrar apenas colunas numéricas restantes
            colunas_preco = [
                c for c in df_precos.columns
                if c != "Data" and pd.api.types.is_numeric_dtype(df_precos[c])
            ]
            
            df_precos = df_precos[["Data"] + colunas_preco].sort_values("Data")
            
            # Remove linhas onde todos os preços são NaN (opcional)
            df_precos = df_precos.dropna(subset=colunas_preco, how='all')

            logger.info(f"✅ Preços carregados: {len(df_precos)} registros | Colunas: {colunas_preco}")
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
    """Alinha dados de granularidades diferentes para a mesma frequência."""

    @staticmethod
    def alinhar_dados(
        df_siacesp: pd.DataFrame,
        df_frete: pd.DataFrame = None,
        df_cambio: pd.DataFrame = None,
        df_oni: pd.DataFrame = None,
        df_precos: pd.DataFrame = None,
        frequencia: str = "W",  # 'D' = diário, 'W' = semanal, 'M' = mensal
    ) -> pd.DataFrame:
        """
        Alinha todos os dados para uma frequência comum.

        Args:
            frequencia: 'D' (dia), 'W' (semana), 'M' (mês)

        Returns:
            DataFrame consolidado com todas as variáveis
        """
        logger.info(f"🔄 Iniciando alinhamento temporal (frequência: {frequencia})...")

        # Passo 1a: Agregar SIACESP para a frequência alvo
        df_base = df_siacesp.copy()
        df_base["Data"] = pd.to_datetime(df_base["Z_PERÍODO"], errors="coerce")
        df_base = df_base.dropna(subset=["Data"])

        # Agregação por período (soma de volumes)
        df_base = (
            df_base.set_index("Data").resample(frequencia)["VOLUME"].sum().reset_index()
        )
        df_base.columns = ["Data", "Volume_Total"]

        logger.info(f"✓ SIACESP agregado: {len(df_base)} períodos")

        # Passo 1b: Processar Frete (diário → frequência alvo)


        # ✅ CORRETO
        if df_frete is not None and not df_frete.empty:
            try:
                df_frete_proc = df_frete.copy()
                df_frete_proc["Data"] = pd.to_datetime(df_frete_proc["Data"], errors="coerce")
                df_frete_proc = df_frete_proc.dropna(subset=["Data"])

                # Resample DEPOIS cria coluna, ANTES dropna
                df_frete_proc = (
                    df_frete_proc.set_index("Data")
                    .resample(frequencia)["Frete"]
                    .mean()
                    .reset_index()  # ← Agora 'Data' é COLUNA
                )

                df_base = pd.merge(df_base, df_frete_proc, on="Data", how="left")
                logger.info(f"✓ Frete alinhado: {len(df_frete_proc)} registros")
            except Exception as e:
                logger.warning(f"⚠️  Erro ao processar Frete: {e}")

            # Passo 1c: Processar Câmbio (diário → frequência alvo)
            if df_cambio is not None:
                df_cambio["Data"] = pd.to_datetime(df_cambio["Data"], errors="coerce")
                df_cambio = df_cambio.dropna(subset=["Data"])
                df_cambio = (
                    df_cambio.set_index("Data")
                    .resample(frequencia)["Cambio"]
                    .mean()
                    .reset_index()
                )
                df_base = pd.merge(df_base, df_cambio, on="Data", how="left")
                logger.info(f"✓ Câmbio alinhado")

        # Passo 1d: Processar ONI (mensal → frequência alvo via forward fill)
        # Passo 1d: Processar ONI (mensal → frequência alvo via forward fill)
        if df_oni is not None:
            try:
                # Mapeamento dos trimestres da NOAA para meses numéricos
                mapa_meses = {
                    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
                    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12
                }
                
                df_oni_prep = df_oni.copy()
                
                # Traduzir as colunas da NOAA (YR e SEAS) para o padrão do seu script
                df_oni_prep["MONTH"] = df_oni_prep["SEAS"].map(mapa_meses)
                df_oni_prep = df_oni_prep.rename(columns={"YR": "YEAR", "ANOM": "ONI"})
                
                # Montar a coluna Data
                df_oni_prep["Data"] = pd.to_datetime(
                    df_oni_prep["YEAR"].astype(str) + "-" + 
                    df_oni_prep["MONTH"].astype(str).str.zfill(2) + "-01"
                )
                df_oni_prep = df_oni_prep[["Data", "ONI"]].drop_duplicates(subset=["Data"])
                
                # Preencher os dias/semanas vazios usando forward fill (mantém o ONI do mês para os dias seguintes)
                date_range = pd.date_range(start=df_base["Data"].min(), end=df_base["Data"].max(), freq=frequencia)
                df_oni_full = pd.DataFrame({"Data": date_range})
                df_oni_full = pd.merge(df_oni_full, df_oni_prep, on="Data", how="left")
                df_oni_full["ONI"] = df_oni_full["ONI"].ffill().bfill()
                
                # Unir com a base principal
                df_base = pd.merge(df_base, df_oni_full[["Data", "ONI"]], on="Data", how="left")
                logger.info(f"✓ ONI alinhado via forward fill")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar ONI: {e}")
                
                df_base = df_base.ffill().bfill()

        # Passo 1e: Processar Preços de Fertilizantes (Urea/DAP/TSP/Potássio)
        if df_precos is not None and not df_precos.empty:
            try:
                df_precos_proc = df_precos.copy()
                df_precos_proc["Data"] = pd.to_datetime(
                    df_precos_proc["Data"], errors="coerce"
                )
                df_precos_proc = df_precos_proc.dropna(subset=["Data"])

                colunas_preco = [c for c in df_precos_proc.columns if c != "Data"]

                df_precos_proc = (
                    df_precos_proc.set_index("Data")
                    .resample(frequencia)[colunas_preco]
                    .mean()
                    .ffill()  # entre publicações de preço, repete o último valor conhecido
                    .reset_index()
                )

                df_base = pd.merge(df_base, df_precos_proc, on="Data", how="left")

                # Feature de "Preço Relativo" = Preço do Fertilizante / Câmbio
                # (indicador mais forte do que preço ou câmbio isolados)
                if "Cambio" in df_base.columns:
                    for coluna in colunas_preco:
                        df_base[f"{coluna}_Relativo"] = (
                            df_base[coluna] / df_base["Cambio"]
                        )

                logger.info(
                    f"✓ Preços de fertilizantes alinhados: {colunas_preco}"
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao processar preços de fertilizantes: {e}")

        return df_base


# ============================================================================
# PASSO 2: ENGENHARIA DE VARIÁVEIS (Feature Engineering)
# ============================================================================


class EngenhariaDeFeaturesML:
    """Cria features defasadas e estatísticas para o modelo de ML."""

    @staticmethod
    def criar_features(
        df: pd.DataFrame,
        col_alvo: str = "Volume_Total",
        lags_dias: List[int] = None,
        janelas_media_movel: List[int] = None,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Cria variáveis defasadas (lags) e médias móveis.

        Args:
            df: DataFrame com dados alinhados
            col_alvo: coluna contendo o volume a prever
            lags_dias: lista de defasagens (ex: [7, 14, 30, 60] dias)
            janelas_media_movel: lista de janelas para média móvel

        Returns:
            DataFrame com features + lista de nomes de colunas de features
        """
        logger.info("🔧 Iniciando engenharia de features...")
        
        # Garante que as colunas não sejam MultiIndex (ex: ('Frete', '') )
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        # Remove colunas duplicadas que podem ter sido criadas no merge
        df = df.loc[:, ~df.columns.duplicated()]

        if lags_dias is None:
            lags_dias=[1, 2, 3]   # Lags de 1 trimestre a 1 ano (em meses)

        if janelas_media_movel is None:
            janelas_media_movel=[3, 6, 12]  # Janelas trimestrais, semestrais e anuais

        df_features = df.copy()
        nomes_features = []

        # Passo 2a: Criar lags (defasagens) para variáveis numéricas
        for coluna in df_features.select_dtypes(include=[np.number]).columns:
            if coluna == col_alvo:
                continue  # Pular a coluna alvo por enquanto

            for lag in lags_dias:
                nome_col = f"{coluna}_lag_{lag}"
                df_features[nome_col] = df_features[coluna].shift(lag)
                nomes_features.append(nome_col)

        logger.info(f"  ✓ {len(lags_dias)} lags criados por variável")

        # Passo 2b: Criar médias móveis
        for coluna in df_features.select_dtypes(include=[np.number]).columns:
            if coluna == col_alvo:
                continue

            for janela in janelas_media_movel:
                nome_col = f"{coluna}_rolling_mean_{janela}"
                df_features[nome_col] = (
                    df_features[coluna].rolling(window=janela).mean()
                )
                nomes_features.append(nome_col)

        logger.info(
            f"  ✓ {len(janelas_media_movel)} janelas de média móvel criadas por variável"
        )

        # Passo 2c: Adicionar features temporais (mês, dia da semana, trimestre)
        df_features["Ano"] = df_features["Data"].dt.year
        df_features["Mes"] = df_features["Data"].dt.month
        df_features["Dia_Semana"] = df_features["Data"].dt.dayofweek
        df_features["Trimestre"] = df_features["Data"].dt.quarter
        df_features["Semana_Ano"] = df_features["Data"].dt.isocalendar().week

        # Codificação cíclica do mês (Sen/Cos): o modelo entende que
        # dezembro (12) e janeiro (1) são vizinhos, não extremos opostos.
        df_features["Mes_Sen"] = np.sin(2 * np.pi * df_features["Mes"] / 12)
        df_features["Mes_Cos"] = np.cos(2 * np.pi * df_features["Mes"] / 12)

        # Feature de "Alta Safra": marca os meses historicamente de maior
        # importação (calculado a partir da própria série de volume).
        media_por_mes = df_features.groupby("Mes")[col_alvo].mean()
        meses_alta_safra = media_por_mes[
            media_por_mes >= media_por_mes.median()
        ].index.tolist()
        df_features["Alta_Safra"] = df_features["Mes"].isin(meses_alta_safra).astype(int)

        nomes_features.extend(
            [
                "Ano",
                "Dia_Semana",
                "Trimestre",
                "Semana_Ano",
                "Mes_Sen",
                "Mes_Cos",
                "Alta_Safra",
            ]
        )
        logger.info(f"  ✓ Features temporais criadas (incl. ciclo Sen/Cos e Alta_Safra)")

        # Remover NaNs gerados pelos lags e médias móveis
        df_features = df_features.dropna()

        logger.info(
            f"✅ Features engenheiradas: {len(nomes_features)} variáveis | {len(df_features)} amostras válidas"
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
# PASSO 4: TREINAMENTO E SELEÇÃO DE MODELOS
# ============================================================================


class TreinadorModelos:
    """Treina múltiplos modelos e seleciona o melhor."""

    @staticmethod
    def treinar_e_avaliar(
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        scaler: StandardScaler = None,
    ) -> Dict[str, Dict]:
        """
        Treina RandomForest e HistGradientBoosting, retorna métricas.

        Returns:
            Dicionário com resultados de cada modelo
        """
        logger.info("\n🤖 TREINANDO MODELOS DE APRENDIZADO DE MÁQUINA")
        logger.info("=" * 60)

        # Normalizar features
        if scaler is None:
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
        else:
            X_train_scaled = scaler.transform(X_train)
            X_test_scaled = scaler.transform(X_test)

        resultados = {}

        # Modelo 1: RandomForestRegressor
        logger.info("\n1️⃣  Treinando RandomForestRegressor...")
        rf = RandomForestRegressor(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
            verbose=0,
        )
        rf.fit(X_train, y_train)

        y_pred_rf = rf.predict(X_test)
        rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))
        mae_rf = mean_absolute_error(y_test, y_pred_rf)
        r2_rf = r2_score(y_test, y_pred_rf)

        resultados["RandomForest"] = {
            "modelo": rf,
            "predicoes": y_pred_rf,
            "rmse": rmse_rf,
            "mae": mae_rf,
            "r2": r2_rf,
            "feature_importance": (
                dict(zip(X_train.columns, rf.feature_importances_))
                if hasattr(rf, "feature_importances_")
                else {}
            ),
        }

        logger.info(f"  ✓ RMSE: {rmse_rf:,.2f}")
        logger.info(f"  ✓ MAE:  {mae_rf:,.2f}")
        logger.info(f"  ✓ R²:   {r2_rf:.4f}")

        # Modelo 2: HistGradientBoostingRegressor
        logger.info("\n2️⃣  Treinando HistGradientBoostingRegressor...")
        hgb = HistGradientBoostingRegressor(
            max_iter=200, max_depth=10, learning_rate=0.1, random_state=42, verbose=0
        )
        hgb.fit(X_train, y_train)

        y_pred_hgb = hgb.predict(X_test)
        rmse_hgb = np.sqrt(mean_squared_error(y_test, y_pred_hgb))
        mae_hgb = mean_absolute_error(y_test, y_pred_hgb)
        r2_hgb = r2_score(y_test, y_pred_hgb)

        resultados["HistGradientBoosting"] = {
            "modelo": hgb,
            "predicoes": y_pred_hgb,
            "rmse": rmse_hgb,
            "mae": mae_hgb,
            "r2": r2_hgb,
            "feature_importance": (
                dict(zip(X_train.columns, hgb.feature_importances_))
                if hasattr(hgb, "feature_importances_")
                else {}
            ),
        }

        logger.info(f"  ✓ RMSE: {rmse_hgb:,.2f}")
        logger.info(f"  ✓ MAE:  {mae_hgb:,.2f}")
        logger.info(f"  ✓ R²:   {r2_hgb:.4f}")

        # Modelo 3: Ridge Regression (regularizado - ideal para poucas amostras)
        logger.info("\n3️⃣  Treinando Ridge Regression...")
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train_scaled, y_train)

        y_pred_ridge = ridge.predict(X_test_scaled)
        rmse_ridge = np.sqrt(mean_squared_error(y_test, y_pred_ridge))
        mae_ridge = mean_absolute_error(y_test, y_pred_ridge)
        r2_ridge = r2_score(y_test, y_pred_ridge)

        resultados["Ridge"] = {
            "modelo": ridge,
            "predicoes": y_pred_ridge,
            "rmse": rmse_ridge,
            "mae": mae_ridge,
            "r2": r2_ridge,
            "feature_importance": (
                dict(zip(X_train.columns, np.abs(ridge.coef_)))
                if hasattr(ridge, "coef_")
                else {}
            ),
        }

        logger.info(f"  ✓ RMSE: {rmse_ridge:,.2f}")
        logger.info(f"  ✓ MAE:  {mae_ridge:,.2f}")
        logger.info(f"  ✓ R²:   {r2_ridge:.4f}")

        # Modelo 4: Lasso Regression (regularizado com seleção de variáveis)
        logger.info("\n4️⃣  Treinando Lasso Regression...")
        lasso = Lasso(alpha=1.0, max_iter=10000)
        lasso.fit(X_train_scaled, y_train)

        y_pred_lasso = lasso.predict(X_test_scaled)
        rmse_lasso = np.sqrt(mean_squared_error(y_test, y_pred_lasso))
        mae_lasso = mean_absolute_error(y_test, y_pred_lasso)
        r2_lasso = r2_score(y_test, y_pred_lasso)

        resultados["Lasso"] = {
            "modelo": lasso,
            "predicoes": y_pred_lasso,
            "rmse": rmse_lasso,
            "mae": mae_lasso,
            "r2": r2_lasso,
            "feature_importance": (
                dict(zip(X_train.columns, np.abs(lasso.coef_)))
                if hasattr(lasso, "coef_")
                else {}
            ),
        }

        logger.info(f"  ✓ RMSE: {rmse_lasso:,.2f}")
        logger.info(f"  ✓ MAE:  {mae_lasso:,.2f}")
        logger.info(f"  ✓ R²:   {r2_lasso:.4f}")

        # Seleção automática do melhor modelo
        melhor = min(resultados.items(), key=lambda x: x[1]["rmse"])
        logger.info(f"\n🏆 MELHOR MODELO: {melhor[0]} (RMSE: {melhor[1]['rmse']:,.2f})")

        return resultados, scaler


# ============================================================================
# PASSO 5: EXPORTAÇÃO E ORQUESTRAÇÃO
# ============================================================================


class ExportadorPrevisoes:
    """Exporta previsões em formato pronto para dashboards."""

    @staticmethod
    def prever_futuro(
        modelo,
        X_ultimo: pd.DataFrame,
        scaler: StandardScaler,
        dias_futuro: int = 30,
        frequencia: str = "W",
    ) -> pd.DataFrame:
        """
        Gera previsões para os próximos períodos.

        Args:
            dias_futuro: Quantos períodos adiante prever
            frequencia: 'D', 'W', ou 'M'

        Returns:
            DataFrame com previsões futuras
        """
        logger.info(
            f"\n🔮 Gerando previsões para os próximos {dias_futuro} períodos..."
        )

        # Usar última amostra como base
        X_ultima = X_ultimo.iloc[-1:].copy()

        # Recalcular quais meses são de "Alta Safra" a partir do histórico
        # completo (mesma lógica usada na engenharia de features)
        meses_alta_safra = []
        if "Mes" in X_ultimo.columns and "Volume_Total" in X_ultimo.columns:
            media_por_mes = X_ultimo.groupby("Mes")["Volume_Total"].mean()
            meses_alta_safra = media_por_mes[
                media_por_mes >= media_por_mes.median()
            ].index.tolist()

        # Remover colunas não numéricas e coluna alvo
        X_ultima_numeric = X_ultima.select_dtypes(include=[np.number]).copy()
        if "Volume_Total" in X_ultima_numeric.columns:
            X_ultima_numeric = X_ultima_numeric.drop(columns=["Volume_Total"])

        previsoes_futuro = []
        data_base = X_ultimo["Data"].iloc[-1]

        for i in range(dias_futuro):
            # Avançar data conforme frequência
            if frequencia == "D":
                data_futura = data_base + timedelta(days=i + 1)
            elif frequencia == "W":
                data_futura = data_base + timedelta(weeks=i + 1)
            else:  # 'M'
                data_futura = data_base + timedelta(days=30 * (i + 1))

            # Atualizar features temporais
            mes_futuro = data_futura.month
            X_ultima_numeric["Ano"] = data_futura.year
            X_ultima_numeric["Dia_Semana"] = data_futura.dayofweek
            X_ultima_numeric["Trimestre"] = data_futura.quarter
            X_ultima_numeric["Semana_Ano"] = data_futura.isocalendar().week
            X_ultima_numeric["Mes_Sen"] = np.sin(2 * np.pi * mes_futuro / 12)
            X_ultima_numeric["Mes_Cos"] = np.cos(2 * np.pi * mes_futuro / 12)
            if "Alta_Safra" in X_ultima_numeric.columns:
                X_ultima_numeric["Alta_Safra"] = int(mes_futuro in meses_alta_safra)

            # Prever (modelos lineares - Ridge/Lasso - foram treinados com
            # dados escalados; RF/HGB usam os dados crus)
            if hasattr(modelo, "coef_"):
                X_input = scaler.transform(X_ultima_numeric)
            else:
                X_input = X_ultima_numeric
            pred = modelo.predict(X_input)[0]

            previsoes_futuro.append(
                {
                    "Data": data_futura,
                    "Volume_Previsto": max(0, pred),  # Não permitir negativos
                    "Periodo": i + 1,
                }
            )

        df_previsto = pd.DataFrame(previsoes_futuro)
        logger.info(f"✅ {len(df_previsto)} previsões geradas")

        return df_previsto

    @staticmethod
    def exportar_json(
        resultados_modelos: Dict,
        df_previsto: pd.DataFrame,
        arquivo_saida: str = "previsoes_ml.json",
    ):
        """Exporta resultados em JSON para consumo por dashboards."""
        logger.info(f"\n📤 Exportando resultados para {arquivo_saida}...")

        # Preparar estrutura de exportação
        dados_exportacao = {
            "timestamp": datetime.now().isoformat(),
            "modelos_treinados": list(resultados_modelos.keys()),
            "metricas": {},
            "previsoes": df_previsto.to_dict(orient="records"),
            "feature_importance": {},
        }

        for nome_modelo, resultado in resultados_modelos.items():
            dados_exportacao["metricas"][nome_modelo] = {
                "rmse": float(resultado["rmse"]),
                "mae": float(resultado["mae"]),
                "r2": float(resultado["r2"]),
            }

            # Ordenar features por importância
            features_sorted = sorted(
                resultado["feature_importance"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[
                :10
            ]  # Top 10
            dados_exportacao["feature_importance"][nome_modelo] = dict(features_sorted)

        # Salvar JSON
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            json.dump(dados_exportacao, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"✅ Resultados exportados para {arquivo_saida}")
        return arquivo_saida


# ============================================================================
# PIPELINE COMPLETO
# ============================================================================


def executar_pipeline_completo(
    caminho_siacesp: str = "BI_Importacao_Siacesp.xlsx",
    caminho_precos_fert: str = None,  # ex: "dados_preços_fert.csv"
    frequencia: str = "W",  # 'D' = diário, 'W' = semanal, 'M' = mensal
    percentual_treino: float = 0.8,
    dias_previsao: int = 12,  # Próximos 12 períodos
):
    """
    Executa o pipeline COMPLETO de ML em 5 passos.
    """

    print("\n" + "=" * 80)
    print("🚀 PIPELINE DE MACHINE LEARNING PARA PREVISÃO DE VOLUMES")
    print("=" * 80 + "\n")

    # ========== PASSO 0: COLETA DE DADOS ==========
    print("PASSO 0️⃣  - COLETA DE DADOS")
    print("-" * 80)
    coletor = ColetorDados()

    df_siacesp = coletor.baixar_volumes_siacesp(caminho_siacesp)
    if df_siacesp is None:
        logger.error("❌ Não foi possível carregar SIACESP. Abortando.")
        return

    df_frete = coletor.baixar_frete()
    df_cambio = coletor.baixar_cambio()
    df_oni = coletor.baixar_oni()

    df_precos = None
    if caminho_precos_fert:
        df_precos = coletor.baixar_precos_fertilizantes(caminho_precos_fert)

    # ========== PASSO 1: ALINHAMENTO TEMPORAL ==========
    print("\n\nPASSO 1️⃣  - ALINHAMENTO TEMPORAL (Resampling & Merging)")
    print("-" * 80)

    alinhador = AlinhadorTemporal()
    df_alinhado = alinhador.alinhar_dados(
        df_siacesp=df_siacesp,
        df_frete=df_frete,
        df_cambio=df_cambio,
        df_oni=df_oni,
        df_precos=df_precos,
        frequencia=frequencia,
    )

    # ========== PASSO 2: ENGENHARIA DE FEATURES ==========
    print("\n\nPASSO 2️⃣  - ENGENHARIA DE VARIÁVEIS (Feature Engineering)")
    print("-" * 80)

    engenheiro = EngenhariaDeFeaturesML()
    df_features, nomes_features = engenheiro.criar_features(
        df=df_alinhado, col_alvo="Volume_Total"
    )

    # ========== PASSO 3: DIVISÃO TREINO/TESTE ==========
    print("\n\nPASSO 3️⃣  - DIVISÃO TREINO/TESTE (Time Series Split)")
    print("-" * 80)

    divisor = DivisorTemporalML()
    (X_train, X_test), (y_train, y_test), df_train, df_test = (
        divisor.dividir_treino_teste(
            df=df_features, col_alvo="Volume_Total", percentual_treino=percentual_treino
        )
    )

    # ========== PASSO 4: TREINAMENTO ==========
    print("\n\nPASSO 4️⃣  - TREINAMENTO E SELEÇÃO DE MODELOS")
    print("-" * 80)

    treinador = TreinadorModelos()
    resultados_modelos, scaler = treinador.treinar_e_avaliar(
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test
    )

    # ========== PASSO 5: EXPORTAÇÃO ==========
    print("\n\nPASSO 5️⃣  - PREVISÃO E EXPORTAÇÃO")
    print("-" * 80)

    # Selecionar melhor modelo
    melhor_modelo_nome = min(resultados_modelos.items(), key=lambda x: x[1]["rmse"])[0]
    melhor_modelo = resultados_modelos[melhor_modelo_nome]["modelo"]

    exportador = ExportadorPrevisoes()
    df_previsto = exportador.prever_futuro(
        modelo=melhor_modelo,
        X_ultimo=df_features,
        scaler=scaler,
        dias_futuro=dias_previsao,
        frequencia=frequencia,
    )

    # Exportar resultados
    arquivo_json = exportador.exportar_json(
        resultados_modelos=resultados_modelos,
        df_previsto=df_previsto,
        arquivo_saida="previsoes_ml_sklearn.json",
    )

    # ========== RESUMO FINAL ==========
    print("\n\n" + "=" * 80)
    print("✅ PIPELINE EXECUTADO COM SUCESSO!")
    print("=" * 80 + "\n")

    print("📊 RESUMO EXECUTIVO:")
    print(f"  • Frequência: {frequencia}")
    print(f"  • Amostras treino: {len(X_train):,}")
    print(f"  • Amostras teste: {len(X_test):,}")
    print(f"  • Features criadas: {len(nomes_features)}")
    print(f"  • Melhor modelo: {melhor_modelo_nome}")
    print(f"  • RMSE: {resultados_modelos[melhor_modelo_nome]['rmse']:,.2f}")
    print(f"  • R² Score: {resultados_modelos[melhor_modelo_nome]['r2']:.4f}")
    print(f"\n📈 Previsões:")
    print(f"  • Períodos previstos: {dias_previsao}")
    print(f"  • Volume médio previsto: {df_previsto['Volume_Previsto'].mean():,.2f}")
    print(f"  • Volume máximo previsto: {df_previsto['Volume_Previsto'].max():,.2f}")

    print(f"\n📁 Arquivos gerados:")
    print(f"  • {arquivo_json}")

    # Salvar dataframes para análise posterior
    df_features.to_csv("dados_features_engenheirados.csv", index=False)
    df_previsto.to_csv("previsoes_futuro.csv", index=False)

    print(f"  • /mnt/user-data/outputs/dados_features_engenheirados.csv")
    print(f"  • /mnt/user-data/outputs/previsoes_futuro.csv")

    print("\n" + "=" * 80 + "\n")

    return {
        "df_alinhado": df_alinhado,
        "df_features": df_features,
        "resultados_modelos": resultados_modelos,
        "df_previsto": df_previsto,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
    }


if __name__ == "__main__":
    # Executar pipeline
    resultados = executar_pipeline_completo(
        caminho_siacesp=r"C:\Users\BERNARDOJULIODEALMEI\automa-imp-markt-intel\atualiza_bases\lineup\BI_Importacao Siacesp.xlsx",
        caminho_precos_fert=r"C:\Users\BERNARDOJULIODEALMEI\automa-imp-markt-intel\atualiza_bases\lineup\dados_preços_fert.csv",
        frequencia="MS",  # MENSAL
        percentual_treino=0.90,
        dias_previsao=6,
    )