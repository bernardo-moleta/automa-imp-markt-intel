"""Baixa os dados de preços de fertilizantes do World Bank e gera um Dataframe."""

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)


""" URL e Configuração para a coleta de dados de preços de fertilizantes."""
url_wb = "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx"


def baixar_dados_fert() -> pd.DataFrame:
    """Baixa os dados de preços de fertilizantes do World Bank e gera um Dataframe."""
    # Lendo a aba específica e pulando as linhas de cabeçalho do relatório
    df_fert = pd.read_excel(url_wb, sheet_name="Monthly Prices", skiprows=6)
    logging.info("Dados de preços de fertilizantes baixados com sucesso.")
    logging.info(df_fert[["Unnamed: 0", "UREA_EE_BULK", "DAP", "TSP"]].tail())

    return df_fert


def main() -> pd.DataFrame:
    """Fluxo de execução: baixar os dados de preços de fertilizantes do World Bank."""
    df_fert = baixar_dados_fert()

    return df_fert
