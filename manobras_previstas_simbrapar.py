import os
import pandas as pd
import requests
from io import StringIO
from colorama import Fore, init

# Inicializa o colorama
init()

# 1. Definir a URL da tabela
url = "http://sinprapar.com.br/PREV.HTM"

# Cabeçalhos para simular o acesso de um navegador real e evitar bloqueios
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def extrair_dados_sinprapar():
    print(f"{Fore.YELLOW}Conectando ao site do SINPRAPAR...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Verifica se a requisição retornou algum erro (ex: 404)

        # 2. Forçar a codificação correta para ler acentuações do português (comum em páginas brasileiras legadas)
        response.encoding = "windows-1252"

        # 3. Ler as tabelas presentes no HTML usando pandas
        # O StringIO é usado para evitar avisos de depreciação de leitura direta de strings
        tabelas = pd.read_html(StringIO(response.text))

        if tabelas:
            # Ajustar o índice para encontrar a tabela com os dados na página
            df = tabelas[1]

            # Remove colunas ou linhas totalmente vazias
            df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)

            # 4. Salva os dados em um arquivo Excel
            nome_arquivo = "Manobras_SINPRAPAR.xlsx"
            
            # Se o arquivo já existir, adiciona um sufixo para não sobrescrever
            if os.path.exists(nome_arquivo):

                base, ext = os.path.splitext(nome_arquivo)
                contador = 1
                while os.path.exists(f"{base}_{contador}{ext}"):
                    contador += 1
                nome_arquivo = f"{base}_{contador}{ext}"
                
            df.to_excel(nome_arquivo, index=False, engine="openpyxl")

            print(f"{Fore.GREEN}Sucesso! Extraídos {len(df)} registros.")
            print(f"{Fore.GREEN}Os dados foram salvos no arquivo: {nome_arquivo}")

        else:
            print(f"{Fore.RED}A página foi carregada, mas nenhuma estrutura de tabela foi encontrada.")

    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Erro de conexão ao tentar acessar o site: {e}")
    except ValueError as e:
        print(f"{Fore.RED}Erro ao processar as tabelas do HTML: {e}")


def main():
    extrair_dados_sinprapar()


if __name__ == "__main__":
    main()
