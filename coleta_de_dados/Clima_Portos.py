import pandas as pd
import datetime

hoje = datetime.date.today().strftime('%Y-%m-%d')
inicio_ano = "2024-01-01"
estacao_paranagua = "A807"

url_clima = f"https://apitempo.inmet.gov.br/estacao/diaria/{inicio_ano}/{hoje}/{estacao_paranagua}"
df_clima = pd.read_json(url_clima)
# A coluna 'CHUVA' contém a precipitação diária
print(df_clima[['DT_MEDICAO', 'CHUVA']].tail())