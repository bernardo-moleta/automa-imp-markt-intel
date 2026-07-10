import pdfplumber
import pandas as pd
import re
import os


def extrair_pdf_para_excel(caminho_pdf, caminho_excel):
    print(f"\nIniciando a leitura do arquivo: {caminho_pdf}...")

    dados_tabela = []

    # Abre o PDF usando pdfplumber
    with pdfplumber.open(caminho_pdf) as pdf:
        for num_pagina, pagina in enumerate(pdf.pages):

            # Configurações de extração de tabela cruciais para PDFs sem grades:
            configuracoes_tabela = {
                "vertical_strategy": "text",
                "horizontal_strategy": "lines",
                "intersection_tolerance": 15,
            }

            tabela = pagina.extract_table(configuracoes_tabela)

            if tabela:
                # Se for a primeira página, pegamos o cabeçalho e os dados
                if num_pagina == 0:
                    dados_tabela.extend(tabela)
                else:
                    # Nas páginas seguintes, ignoramos o cabeçalho
                    dados_tabela.extend(tabela[1:])
            else:
                print(f"Aviso: Nenhuma tabela encontrada na página {num_pagina + 1}.")

    if not dados_tabela:
        print("Erro: Não foi possível extrair dados da tabela com as configurações atuais.")
        return

    # Limpeza dos dados:
    dados_limpos = []
    for linha in dados_tabela:
        linha_limpa = []
        for celula in linha:
            if celula:
                # Remove quebras de linha e espaços extras
                celula_limpa = re.sub(r"\s+", " ", str(celula)).strip()
                linha_limpa.append(celula_limpa)
            else:
                linha_limpa.append("")
        dados_limpos.append(linha_limpa)

    # Cria o DataFrame do Pandas
    colunas = dados_limpos[0]
    linhas = dados_limpos[1:]

    df = pd.DataFrame(linhas, columns=colunas)

    # Opcional: Converter colunas numéricas de padrão brasileiro (1.000,50) para float
    for col in df.columns[1:]:  # Ignora a primeira coluna (ex: 'OPERADOR')
        df[col] = df[col].apply(
            lambda x: (
                pd.to_numeric(x.replace(".", "").replace(",", "."), errors="ignore")
                if isinstance(x, str)
                else x
            )
        )

    # Exporta para Excel
    try:
        df.to_excel(caminho_excel, index=False, engine="openpyxl")
        print(f"Sucesso! Arquivo Excel gerado em: {caminho_excel}")
    except Exception as e:
        print(f"Erro ao salvar o arquivo Excel: {e}")


def encontrar_arquivo_pdf(palavra_chave):
    """
    Busca no diretório atual o primeiro arquivo PDF que contenha a palavra-chave no nome.
    """
    diretorio_atual = os.getcwd()
    
    for arquivo in os.listdir(diretorio_atual):
        # Transforma tudo em maiúsculo para evitar erros de case-sensitive (ex: produto vs PRODUTO)
        if palavra_chave.upper() in arquivo.upper() and arquivo.lower().endswith('.pdf'):
            return arquivo
            
    print(f"Aviso: Nenhum arquivo PDF contendo '{palavra_chave}' foi encontrado na pasta atual.")
    return None


def operador():
    arquivo_entrada = encontrar_arquivo_pdf("OPERADORES")
    if arquivo_entrada:
        arquivo_saida = "Relatorio_Operadores.xlsx"
        extrair_pdf_para_excel(arquivo_entrada, arquivo_saida)


def importador():
    arquivo_entrada = encontrar_arquivo_pdf("IMPORTADOR")
    if arquivo_entrada:
        arquivo_saida = "Relatorio_Importadores.xlsx"
        extrair_pdf_para_excel(arquivo_entrada, arquivo_saida)


def produto():
    arquivo_entrada = encontrar_arquivo_pdf("PRODUTO")
    if arquivo_entrada:
        arquivo_saida = "Relatorio_Produtos.xlsx"
        extrair_pdf_para_excel(arquivo_entrada, arquivo_saida)


def main():
    print("Iniciando processamento em lote...")
    operador()
    importador()
    produto()
    print("\nProcessamento concluído.")


if __name__ == "__main__":
    main()