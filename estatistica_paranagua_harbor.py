import pdfplumber
import pandas as pd
import re


def extrair_pdf_para_excel(caminho_pdf, caminho_excel):
    print(f"Iniciando a leitura do arquivo: {caminho_pdf}...")

    dados_tabela = []

    # Abre o PDF usando pdfplumber
    with pdfplumber.open(caminho_pdf) as pdf:
        for num_pagina, pagina in enumerate(pdf.pages):

            # Configurações de extração de tabela cruciais para PDFs sem grades:
            # - vertical_strategy="text": usa o alinhamento das palavras para adivinhar as colunas.
            # - horizontal_strategy="lines": usa as linhas horizontais que você mencionou que existem.
            # - intersection_tolerance: ajusta a sensibilidade para cruzar linhas e texto.
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
                    # Nas páginas seguintes, ignoramos o cabeçalho (assumindo que a linha 0 é cabeçalho)
                    # Caso o cabeçalho não se repita nas outras páginas, mude para: dados_tabela.extend(tabela)
                    dados_tabela.extend(tabela[1:])
            else:
                print(f"Aviso: Nenhuma tabela encontrada na página {num_pagina + 1}.")

    if not dados_tabela:
        print(
            "Erro: Não foi possível extrair dados da tabela com as configurações atuais."
        )
        return

    # Limpeza dos dados:
    # Às vezes o pdfplumber traz quebras de linha (\n) dentro das células ou valores nulos.
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
    # A primeira linha da lista torna-se as colunas (ex: OPERADOR, JAN, FEV, MAR...)
    colunas = dados_limpos[0]
    linhas = dados_limpos[1:]

    df = pd.DataFrame(linhas, columns=colunas)

    # Opcional: Converter colunas numéricas de padrão brasileiro (1.000,50) para float
    # Isso garante que no Excel elas sejam tratadas como números e não como texto.
    for col in df.columns[1:]:  # Ignora a coluna 'OPERADOR'
        # Remove pontos de milhar, troca vírgula por ponto e converte para float
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


# Execução principal
def operador():
    arquivo_entrada_operador = r"C:\Users\BERNARDOJULIODEALMEI\BRFERTIL S.A\Importação - 00. Market Intel 2026\ESTATISTICAS PARANAGUA - HARBOR\DIFERENÇA HARBOR PARA OUTROS OPERADORES - JANEIRO A MAIO.pdf"
    arquivo_saida_operador = r"C:\Users\BERNARDOJULIODEALMEI\BRFERTIL S.A\Importação - 00. Market Intel 2026\ESTATISTICAS PARANAGUA - HARBOR\Relatorio_Operadores.xlsx"

    extrair_pdf_para_excel(arquivo_entrada_operador, arquivo_saida_operador)


def importador():
    arquivo_entrada_importador = r"C:\Users\BERNARDOJULIODEALMEI\BRFERTIL S.A\Importação - 00. Market Intel 2026\ESTATISTICAS PARANAGUA - HARBOR\RESUMO DE DESCARGA POR IMPORTADOR - JANEIRO A MAIO.pdf"
    arquivo_saida_importador = r"C:\Users\BERNARDOJULIODEALMEI\BRFERTIL S.A\Importação - 00. Market Intel 2026\ESTATISTICAS PARANAGUA - HARBOR\Relatorio_Importadores.xlsx"

    extrair_pdf_para_excel(arquivo_entrada_importador, arquivo_saida_importador)


def produto():
    arquivo_entrada_produto = r"C:\Users\BERNARDOJULIODEALMEI\BRFERTIL S.A\Importação - 00. Market Intel 2026\ESTATISTICAS PARANAGUA - HARBOR\RESUMO DE DESCARGA POR PRODUTO - JANEIRO A MAIO.pdf"
    arquivo_saida_produto = r"C:\Users\BERNARDOJULIODEALMEI\BRFERTIL S.A\Importação - 00. Market Intel 2026\ESTATISTICAS PARANAGUA - HARBOR\Relatorio_Produtos.xlsx"

    extrair_pdf_para_excel(arquivo_entrada_produto, arquivo_saida_produto)


def main():
    operador()
    importador()
    produto()


if __name__ == "__main__":
    main()
