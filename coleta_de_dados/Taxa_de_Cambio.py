"""Baixa os dados de taxa de câmbio do dólar e gera um Dataframe."""

import pandas as pd
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

""" URL e Configuração para a coleta de dados de taxa de câmbio."""
URL_DOLAR = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json&dataInicial=01/01/2020&"

# A API do Bacen retorna 406 se a requisição não tiver um User-Agent "de navegador"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def baixar_dados_cambio() -> pd.DataFrame:
    """Baixa os dados de taxa de câmbio do dólar e gera um Dataframe."""
    resposta = requests.get(URL_DOLAR, headers=HEADERS, timeout=30)
    resposta.raise_for_status()

    df_dolar = pd.DataFrame(resposta.json())
    df_dolar["data"] = pd.to_datetime(df_dolar["data"], format="%d/%m/%Y")
    df_dolar["valor"] = df_dolar["valor"].astype(float)

    logger.info("Dados de câmbio baixados com sucesso. %d linhas.", len(df_dolar))
    logger.info(df_dolar.tail())
    return df_dolar


def main() -> pd.DataFrame:
    """Fluxo de execução: baixar os dados de taxa de câmbio do dólar."""
    df_dolar = baixar_dados_cambio()
    print(df_dolar.tail())
    return df_dolar


if __name__ == "__main__":
    main()
