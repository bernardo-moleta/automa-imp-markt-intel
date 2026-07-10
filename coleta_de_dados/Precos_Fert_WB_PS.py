import pandas as pd

url_wb = "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx"
# Lendo a aba específica e pulando as linhas de cabeçalho do relatório
df_fert = pd.read_excel(url_wb, sheet_name="Monthly Prices", skiprows=6)
print(df_fert[['Unnamed: 0', 'UREA_EE_BULK', 'DAP', 'TSP']].tail())