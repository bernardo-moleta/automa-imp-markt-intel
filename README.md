## INFO - DASHBOARD

A arquitetura do projeto apresenta um pipeline sólido para validação de dados logísticos e escalação. Ao calcular o desvio volumétrico e exportar diretamente um payload em formato JavaScript, a solução desacopla a pesada lógica de processamento em Python da camada de apresentação. Essa abordagem transforma os dados brutos em conhecimento estratégico com baixo custo computacional e extrema agilidade no front-end.

Para suportar a evolução e crescimento da ferramenta, o ecossistema pode ser expandido além da arquitetura atual. Integrar os resultados do agrupamento em um banco de dados analítico em nuvem (como Google BigQuery) permitiria explorar um histórico ilimitado sem afetar a performance do navegador. Além disso, a atual projeção com o Prophet poderia ser enriquecida futuramente com outras bibliotecas de Machine Learning (como Scikit-learn), permitindo injetar variáveis de mercado na análise para antecipar picos ou quedas nas operações.


# Análise Comparativa de Escalação e Confiabilidade

Este projeto consiste em uma solução de inteligência e automação projetada para validar a precisão da escalação marítima (Line Up) contra a base consolidada do SIACESP. O fluxo extrai e consolida as bases gerando uma visão comparativa clara de volumes e discrepâncias operacionais.

A camada de visualização foca em apresentar os KPIs críticos em uma interface *premium*, com tipografia austera, design minimalista e ausência de ornamentos desnecessários.

## Tecnologias e Arquitetura

* **Processamento de Dados:** Construído em Python, empregando a biblioteca `pandas` para executar agregações, aplicação de regras de negócio e *outer merges* nas fontes `.xlsx`.
* **Modelagem Preditiva:** Integra o pacote `prophet` para projetar tendências futuras com base nos registros passados.
* **Geração de Relatórios:** Utiliza o `openpyxl` para formatar e persistir os resultados detalhados diretamente em planilhas customizadas.
* **Visualização:** Dashboard desacoplado, desenvolvido com HTML, CSS e Vanilla JavaScript, com renderização de gráficos complexos via `Chart.js`.
* **Integração:** O motor em Python converte os quadros de dados na saída estática `dados_dashboard.js`, que alimenta o painel de forma instantânea.
  INSTRUÇÕES.md
  Markdown

# Guia de Configuração e Execução

Siga os passos abaixo para preparar o ambiente analítico e realizar as atualizações de ciclo de dados do painel.

## 1. Preparação do Ambiente

* É estritamente necessário ter a linguagem Python configurada no ambiente operacional local.
* Instale as bibliotecas requeridas para a manipulação dos cálculos e modelos rodando o comando: `pip install pandas openpyxl prophet`.

## 2. Estrutura de Arquivos

* Assegure-se de que o algoritmo principal `confiabilidade_verdadeiro.py` encontre as origens das planilhas logísticas dentro da estrutura de pastas esperada pelo código.

## 3. Executando o Pipeline

* Para iniciar o cruzamento, execute o processador via terminal com `python confiabilidade_verdadeiro.py`.
* O algoritmo limpará os dados, aplicará as regressões preditivas e gerará o arquivo `dados_dashboard.js` de modo automatizado.
* Para cenários de operação assídua (como o acompanhamento ininterrupto de importação de insumos como MOP, MAP e Ureia), recomenda-se que a invocação deste script seja alocada em uma *DAG* do Apache Airflow para garantir orquestração e recorrência de rotina sem intervenção manual.

## 4. Visualizando o Dashboard

* Assim que a execução em Python for concluída e o novo arquivo `.js` for gerado, abra o arquivo `dashboard_comparativo.html` diretamente em um navegador web.
* A leitura da arquitetura client-side exime a necessidade de iniciar servidores locais, permitindo a navegação imediata pelas abas de 'S&OP Semanal', pesquisa avançada e resumos consolidados.


# Ideias de implementações e escalabilidade:

A transição do Prophet para modelos do Scikit-learn (como Random Forest, Gradient Boosting ou SVR) exige a construção de matrizes de features (exógenas), já que esses algoritmos não lidam nativamente com o tempo da mesma forma que os modelos univariados.

Para refinar a precisão das projeções logísticas e marítimas — especialmente considerando o fluxo de insumos como MOP, MAP e Ureia —, a inclusão das seguintes categorias de variáveis enriqueceria substancialmente o modelo:

1. Dinâmica de Mercado e Custos
   Taxa de Câmbio (BRL/USD) com Defasagem (Lag): Fertilizantes são dolarizados. Uma taxa de câmbio favorável ou desfavorável impacta a decisão de compra, refletindo no volume de navios que chegarão 60 a 90 dias depois. Adicionar variáveis como cambio_lag_60 e cambio_lag_90 ajuda o algoritmo a capturar esse atraso operacional.

Preços Internacionais (CFR Brasil): O histórico de preços das próprias commodities (Ureia, MAP, MOP). Quedas bruscas nos preços costumam gerar picos de aquisição, congestionando o Line Up marítimo meses depois.

Baltic Dry Index (BDI): O principal indicador global do custo de frete marítimo para carga seca a granel. Fretes mais caros podem atrasar ou fracionar o volume das escalas.

2. Sazonalidade Agrícola e Calendário
   Distância para as Janelas de Plantio: Em vez de usar apenas o "mês" como variável, você pode criar uma feature contínua (ex: dias_para_plantio_soja ou dias_para_safrinha). O volume de atracação sobe drasticamente à medida que essas janelas se aproximam.

Expectativa de Área Plantada (CONAB): A variação percentual da estimativa de área a ser cultivada no Brasil dita o teto da demanda por fertilizantes no ano.

3. Gargalos Logísticos e Operacionais
   Tempo Médio de Espera (Fila de Navios): Variáveis que capturam o nível de congestionamento atual nos principais portos (como Paranaguá e Santos). Se o porto já apresenta um demurrage (tempo de espera) alto, o volume efetivamente descarregado nos meses seguintes pode ser menor que o volume nominal esperado.

Volume em Trânsito (Navios Nomeados): O total de carga que já consta no sistema com status de "em viagem", atuando como um forte preditor de curtíssimo prazo.

4. Condições Climáticas (Macro)
   Índices ENSO (El Niño / La Niña): Anomalias de temperatura do oceano afetam a confiança do produtor nas chuvas. Anos de secas previstas reduzem a compra de pacotes tecnológicos (menos fertilizantes), impactando o planejamento logístico a longo prazo.

Como estruturar no código:
No Scikit-learn, o segredo para trabalhar com essas variáveis em séries temporais é a engenharia de lags (valores passados) e médias móveis (rolling means). Um navio que atraca em maio é o resultado de uma equação econômica resolvida em fevereiro.

O pipeline precisaria criar essas colunas retrospectivas no DataFrame do Pandas antes de alimentar os algoritmos do sklearn, transformando os dados brutos de mercado em sinais de antecipação para o dashboard.
