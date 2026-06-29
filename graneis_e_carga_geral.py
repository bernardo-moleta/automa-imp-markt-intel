import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extrair_relatorios_recentes():
    """
    Varre a página operacional e efetua o download da versão mais
    recente dos documentos mapeados na variável 'alvos'.
    """
    url_base = "https://www.portosdoparana.pr.gov.br/Operacional/Pagina/Graneis-de-Importacao-e-Carga-Geral"
    
    # Headers para simular um navegador e evitar bloqueios (Error 403)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }

    # Defina aqui as partes fixas do texto que identificam os documentos.
    # Ajuste as strings abaixo para refletirem exatamente os dois links destacados na sua imagem.
    alvos = [
        "LINE UP DE GRANÉIS SÓLIDOS DE IMPORTAÇÃO",
        "LINE UP DE CARGA GERAL"
        # Se os seus alvos forem as atas, pode alterar para "ATA No 082" ou similar
    ]

    arquivos_baixados = []

    try:
        print(f"Acessando {url_base}...")
        
        # O verify=False garante o acesso mesmo se os certificados SSL do governo estiverem desatualizados
        response = requests.get(url_base, headers=headers, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extrai todas as tags de link da página
        links_pagina = soup.find_all('a', href=True)
        
        for alvo in alvos:
            # Varre a página de cima para baixo em busca do termo alvo
            for link in links_pagina:
                texto_link = link.text.strip().upper()
                
                # O operador 'in' identifica o documento independentemente da data que o sufixa
                if alvo.upper() in texto_link:
                    url_pdf = urljoin(url_base, link['href'])
                    
                    # Higieniza o texto do site para criar um nome de arquivo válido no Windows/Linux
                    nome_seguro = "".join(c for c in texto_link if c.isalnum() or c in (' ', '-', '_')).strip()
                    nome_arquivo = f"{nome_seguro}.pdf"
                    
                    print(f"\n[+] Alvo encontrado: {texto_link}")
                    print(f"    Efetuando download: {url_pdf}")
                    
                    pdf_response = requests.get(url_pdf, headers=headers, verify=False)
                    pdf_response.raise_for_status()
                    
                    # Salva o arquivo diretamente no diretório atual de execução
                    caminho_destino = os.path.join(os.getcwd(), nome_arquivo)
                    with open(caminho_destino, 'wb') as f:
                        f.write(pdf_response.content)
                        
                    print(f"    Salvo com sucesso em: {caminho_destino}")
                    arquivos_baixados.append(caminho_destino)
                    
                    # O 'break' garante que apenas o primeiro arquivo encontrado (o mais recente)
                    # seja baixado. Assim, ele interrompe a busca por esse alvo e pula para o próximo.
                    break
                    
        return arquivos_baixados

    except requests.exceptions.RequestException as e:
        print(f"Falha na requisição web: {e}")
        return []

if __name__ == "__main__":
    # Desabilita os alertas de segurança SSL exibidos no terminal
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    extrair_relatorios_recentes()
    
#TODO: Salvar os arquivos no caminho específico