import pandas as pd

url_dolar = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json"
df_dolar = pd.read_json(url_dolar)
df_dolar['data'] = pd.to_datetime(df_dolar['data'], format='%d/%m/%Y')
print(df_dolar.tail())