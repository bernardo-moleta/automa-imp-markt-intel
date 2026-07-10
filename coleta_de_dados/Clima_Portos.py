"""Baixar dados de clima da estação meteorológica de Paranaguá (A807) do INMET."""

import pandas as pd
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)

"""Configuração e datas para a coleta de dados climáticos"""
hoje = datetime.date.today().strftime("%Y-%m-%d")
inicio_ano = "2024-01-01"
estacao_paranagua = "A807"


"""URL e Configuração para a coleta de dados climáticos"""
url_clima = f"https://apitempo.inmet.gov.br/estacao/diaria/{inicio_ano}/{hoje}/{estacao_paranagua}"


def baixar_dados_clima() -> pd.DataFrame:
    """Baixa os dados e gera um Dataframe."""

    df_clima = pd.read_json(url_clima)

    # A coluna 'CHUVA' contém a precipitação diária
    logging.info("Dados de clima baixados com sucesso.")
    logging.info(df_clima[["DT_MEDICAO", "CHUVA"]].tail())

    return df_clima


def main() -> pd.DataFrame:
    """Fluxo de execução: baixar os dados de clima da estação meteorológica de Paranaguá."""
    df_clima = baixar_dados_clima()

    return df_clima


if __name__ == "__main__":
    main()
