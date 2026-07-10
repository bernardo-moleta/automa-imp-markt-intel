'''Baixa os dados de taxa de câmbio do dólar e gera um Dataframe.'''

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)

""" URL e Configuração e datas para a coleta de dados de taxa de câmbio."""
url_dolar = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json"


def baixar_dados_cambio() -> pd.DataFrame:
    """Baixa os dados de taxa de câmbio do dólar e gera um Dataframe."""
    df_dolar = pd.read_json(url_dolar)
    df_dolar["data"] = pd.to_datetime(df_dolar["data"], format="%d/%m/%Y")

    logging.info("Dados de câmbio baixados com sucesso.")
    logging.info(df_dolar.tail())

    return df_dolar


def main() -> pd.DataFrame:
    """Fluxo de execução: baixar os dados de taxa de câmbio do dólar."""
    df_dolar = baixar_dados_cambio()

    return df_dolar
