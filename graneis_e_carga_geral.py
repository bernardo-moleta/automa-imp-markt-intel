import os
import requests
import pandas as pd
import pdfplumber
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
from colorama import Fore, Style, init

# Inicializa o colorama
init()

# Desativa os alertas poluentes de requisições sem verificação SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def converter_pdf_para_excel(caminho_pdf):
    """Lê o arquivo PDF, extrai as matrizes da tabela e salva em formato Excel (.xlsx)"""
    # Define o nome do arquivo de saída substituindo a extensão .pdf por .xlsx
    nome_base = os.path.splitext(caminho_pdf)[0]
    caminho_excel = f"{nome_base}.xlsx"

    print(f"{Fore.YELLOW}    [>] Convertendo o PDF para Excel...")
    dados_extraidos = []

    # Abre o PDF e varre todas as páginas disponíveis
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            # A função extract_tables() procura por grades/linhas físicas na página
            tabelas = pagina.extract_tables()

            for tabela in tabelas:
                for linha in tabela:
                    # Os PDFs geralmente possuem quebras de linha (\n) dentro das células.
                    # Substituímos por " / " para evitar que a linha quebre no Excel.
                    linha_limpa = [
                        str(celula).replace("\n", " / ") if celula else ""
                        for celula in linha
                    ]
                    dados_extraidos.append(linha_limpa)

    # Verifica se encontrou alguma estrutura de tabela válida
    if dados_extraidos:
        # Pega a primeira linha capturada como cabeçalho e as demais como dados
        df = pd.DataFrame(dados_extraidos[1:], columns=dados_extraidos[0])

        # Salva o resultado no disco
        df.to_excel(caminho_excel, index=False, engine="openpyxl")
        print(f"{Fore.GREEN}    [+] Sucesso! Planilha salva em: {caminho_excel}")
    else:
        print(f"{Fore.RED}    [-] Não foi possível detectar grades de tabela neste PDF.")


def extrair_e_converter_relatorios():
    url_base = "https://www.portosdoparana.pr.gov.br/Operacional/Pagina/Graneis-de-Importacao-e-Carga-Geral"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    alvos = ["LINE UP DE GRANÉIS SÓLIDOS DE IMPORTAÇÃO", "LINE UP DE CARGA GERAL"]

    try:
        # Acesso ao site (ignorando SSL)
        response = requests.get(url_base, headers=headers, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links_pagina = soup.find_all("a", href=True)

        for alvo in alvos:
            for link in links_pagina:
                texto_link = link.text.strip().upper()

                # Valida se o alvo está no texto (independente da data)
                if alvo.upper() in texto_link:
                    url_pdf = urljoin(url_base, link["href"])

                    # Normaliza o nome para evitar erros ao salvar no Windows/Linux
                    nome_seguro = "".join(
                        c for c in texto_link if c.isalnum() or c in (" ", "-", "_")
                    ).strip()
                    caminho_pdf = os.path.join(os.getcwd(), f"{nome_seguro}.pdf")

                    print(f"{Fore.GREEN}\n[+] Documento Encontrado: {texto_link}")
                    print(f"{Fore.CYAN}    Baixando: {url_pdf}")

                    # Faz o download do PDF
                    pdf_response = requests.get(url_pdf, headers=headers, verify=False)
                    with open(caminho_pdf, "wb") as f:
                        f.write(pdf_response.content)

                    # Aciona a conversão após o arquivo ser salvo
                    converter_pdf_para_excel(caminho_pdf)

                    # Interrompe o loop para processar apenas o mais recente
                    break

    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Erro durante a conexão web: {e}")
    except Exception as e:
        print(f"{Fore.RED}Erro durante a conversão: {e}")


def main():
    extrair_e_converter_relatorios()


if __name__ == "__main__":
    main()
