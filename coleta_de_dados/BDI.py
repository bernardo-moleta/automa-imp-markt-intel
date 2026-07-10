"""Baixa os dados do BDRY (Breakwave Dry Bulk Shipping ETF)."""

import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)


def baixar_dados_frete():
    """Baixa os dados do BDRY (Breakwave Dry Bulk Shipping ETF)."""
    # O BDRY (Breakwave Dry Bulk Shipping ETF), espelha o custo de frete a granel.
    df_frete = yf.download("BDRY", start="2020-01-01")

    logging.info("Dados de frete baixados com sucesso.")
    logging.info(df_frete["Close"].tail())

    return df_frete


def transforma_em_dataframe(df_frete):
    """Transforma os dados do BDRY em um DataFrame."""
    df_frete = df_frete.reset_index()
    df_frete = df_frete.rename(columns={"Date": "Data", "Close": "Frete"})
    df_frete = df_frete[["Data", "Frete"]]

    logging.info("Dados de frete transformados com sucesso.")

    return df_frete


def main():
    """Fluxo de execução: baixar e transformar os dados do BDRY."""
    df_frete = baixar_dados_frete()
    df_frete = transforma_em_dataframe(df_frete)

    logging.info("Dados de frete prontos para uso.")

    return df_frete


if __name__ == "__main__":
    main()
