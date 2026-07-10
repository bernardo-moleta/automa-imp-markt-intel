"""Baixa os dados de ONI (Oceanic Niño Index) e gera um Dataframe."""

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)


"""Url e Configuração para a coleta de dados de ONI (Oceanic Niño Index)"""
url_enso = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"


def baixar_dados_oni() -> pd.DataFrame:
    """Baixa os dados de ONI (Oceanic Niño Index) e gera um Dataframe."""
    # Lendo o arquivo de texto com os dados de ONI
    # O sep=r'\s+' diz ao pandas para separar as colunas por qualquer quantidade de espaços
    df_enso = pd.read_csv(url_enso, sep=r"\s+")

    logging.info("Dados de ONI baixados com sucesso.")
    logging.info(df_enso.head())

    return df_enso


def main() -> pd.DataFrame:
    """Fluxo de execução: baixar os dados de ONI (Oceanic Niño Index)."""
    df_enso = baixar_dados_oni()

    return df_enso


if __name__ == "__main__":
    main()
