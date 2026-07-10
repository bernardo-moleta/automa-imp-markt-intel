import pandas as pd

url_enso = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
# O sep=r'\s+' diz ao pandas para separar as colunas por qualquer quantidade de espaços
df_enso = pd.read_csv(url_enso, sep=r'\s+')
print(df_enso.head())