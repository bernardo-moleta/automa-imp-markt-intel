import yfinance as yf

# O ticker ^BDI nem sempre está estável no Yahoo Finance dependendo da região. 
# Uma alternativa sólida usada em modelagem é o BDRY (Breakwave Dry Bulk Shipping ETF), 
# que espelha o custo de frete a granel.
df_frete = yf.download("BDRY", start="2020-01-01")
print(df_frete['Close'].tail())