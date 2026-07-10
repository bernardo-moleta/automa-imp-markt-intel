"""Baixa os dados de preços de fertilizantes do World Bank e gera um DataFrame."""

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL_WB = "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx"
SHEET_NAME = "Monthly Prices"

# Colunas de interesse (nomes usados atualmente pelo World Bank na planilha)
COLUNAS_ALVO = [
    "Unnamed: 0",
    "Urea ",
    "DAP",
    "TSP",
    "Potassium chloride **",
]

hoje = pd.Timestamp.now().strftime("%Y-%m-%d")

def baixar_dados_raw(caminho: str = URL_WB) -> pd.DataFrame:
    """Baixa a aba 'Monthly Prices' e remove as linhas de cabeçalho/unidade do relatório."""
    logger.info(f"Baixando dados de fertilizantes do World Bank do dia: {hoje}")

    df = pd.read_excel(caminho, sheet_name=SHEET_NAME, skiprows=4)
    # A primeira linha após o cabeçalho traz as unidades (ex: '($/bbl)'), não dados
    df = df.iloc[1:].reset_index(drop=True)

    logger.info("Dados baixados com sucesso. %d linhas.", len(df))
    return df


def formatar_dados_fert(df_fert_raw: pd.DataFrame) -> pd.DataFrame:
    """Seleciona apenas as colunas de fertilizantes de interesse."""
    colunas_disponiveis = [c for c in COLUNAS_ALVO if c in df_fert_raw.columns]

    faltando = set(COLUNAS_ALVO) - set(colunas_disponiveis)
    if faltando:
        logger.warning("Colunas não encontradas no arquivo: %s", faltando)

    df_fert_clean = df_fert_raw[colunas_disponiveis].rename(columns={"Unnamed: 0": "Data"})
    return df_fert_clean


def main(caminho: str = URL_WB) -> pd.DataFrame:
    """Fluxo de execução: baixar e formatar os dados de preços de fertilizantes."""
    df_fert_raw = baixar_dados_raw(caminho)
    df_fert = formatar_dados_fert(df_fert_raw)
    return df_fert


if __name__ == "__main__":
    main()
