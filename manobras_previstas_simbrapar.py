#Cria excel a partir dos dados do link: https://www.sinprapar.com.br/PREV.HTM
import pandas as pd
import requests
from io import StringIO
from datetime import datetime

#configs
data_de_extracao = datetime.now().strftime("%Y-%m-%d_%H-%M")

# 1. Definir a URL da tabela
url = 'http://sinprapar.com.br/PREV.HTM'

# Cabeçalhos para simular o acesso de um navegador real e evitar bloqueios (Error 403/406)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

print("Conectando ao site do SINPRAPAR...")
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status() # Verifica se a requisição retornou algum erro (ex: 404)
    
    # 2. Forçar a codificação correta para ler acentuações do português (comum em páginas brasileiras legadas)
    response.encoding = 'windows-1252'
    
    # 3. Ler as tabelas presentes no HTML usando pandas
    # O StringIO é usado para evitar avisos de depreciação de leitura direta de strings
    tabelas = pd.read_html(StringIO(response.text))
    
    if tabelas:
        # Pega a primeira tabela encontrada na página
        df = tabelas[0]
        
        # Limpeza opcional: remove colunas ou linhas que vieram totalmente vazias
        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
        
        # 4. Salvar os dados em um arquivo Excel
        nome_arquivo = f'manobras_previstas_simbrapar{data_de_extracao}.xlsx'
        df.to_excel(nome_arquivo, index=False, engine='openpyxl')
        
        print(f"Sucesso! Extraídos {len(df)} registros.")
        print(f"Os dados foram salvos no arquivo: {nome_arquivo}")
        
    else:
        print("A página foi carregada, mas nenhuma estrutura de tabela foi encontrada.")
        
except requests.exceptions.RequestException as e:
    print(f"Erro de conexão ao tentar acessar o site: {e}")
except ValueError as e:
    print(f"Erro ao processar as tabelas do HTML: {e}")
    
#TODO: Salvar o arquivo no caminho específico