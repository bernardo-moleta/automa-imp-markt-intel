import os
import sys
import pandas as pd
import requests
from io import StringIO
from colorama import Fore, init

init(autoreset=True)

URL = "http://sinprapar.com.br/PREV.HTM"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def caminho_saida():
    """
    Retorna a pasta onde o executável está rodando
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def extrair_dados_sinprapar():
    print(f"{Fore.YELLOW}Conectando ao site do SINPRAPAR...")

    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        response.encoding = "windows-1252"
        tabelas = pd.read_html(StringIO(response.text))

        if not tabelas:
            print(f"{Fore.RED}Nenhuma tabela encontrada.")
            return

        # tabela principal
        df = tabelas[1]
        df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)
        pasta = caminho_saida()
        nome = "Manobras_SINPRAPAR.xlsx"
        arquivo = os.path.join(pasta, nome)
        contador = 1

        while os.path.exists(arquivo):
            arquivo = os.path.join(pasta, f"Manobras_SINPRAPAR_{contador}.xlsx")
            contador += 1

        df.to_excel(arquivo, index=False, engine="openpyxl")

        print(f"{Fore.GREEN}\nSucesso!")
        print(f"{Fore.GREEN}{len(df)} registros extraídos")
        print(f"{Fore.GREEN}Arquivo criado:")
        print(f"{Fore.CYAN}{arquivo}")

    except requests.exceptions.RequestException as erro:
        print(f"{Fore.RED}Erro de conexão:")
        print(erro)

    except Exception as erro:
        print(f"{Fore.RED}Erro inesperado:")
        print(erro)


def main():
    extrair_dados_sinprapar()
    input("\nPressione ENTER para fechar...")


if __name__ == "__main__":
    main()
