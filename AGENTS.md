# Diretrizes do Repositório

## Visão Geral
Este repositório sustenta o TCC que compara valores de viagens em milhas e dinheiro entre Azul, Smiles e um banco histórico próprio. O objetivo duplo do estudo é (1) indicar se a compra deve ser feita em milhas ou dinheiro e (2) sinalizar quando o preço atual se afasta do intervalo histórico. O código mantém tudo simples: coletores pontuais acessam os endpoints públicos das companhias, salvam o JSON bruto e permitem que planilhas ou notebooks externos façam a análise, inclusive o cruzamento com o histórico.

## Estrutura do Projeto e Fluxo
- `smiles_scraper/`: cliente síncrono baseado em `requests` que chama a API REST da Smiles com cookies e cabeçalhos pré-capturados. Funções auxiliares resumem as opções mais baratas de ida e volta antes de persistirem o payload completo em `smiles_output/`, que depois é confrontado com o banco histórico.
- `azul_scraper/`: scripts que usam selenium-driverless (milhas) ou requisições HTTP simples (dinheiro) após repetir um corpo de POST interceptado. Eles reproduzem o fluxo da Smiles, extraindo as menores tarifas em ambos os sentidos e gerando os dados que serão comparados com a Smiles e com o histórico armazenado.
- `azul_scraper_playwright.py`: executor leve em Playwright usado apenas para observar manualmente o site da Azul ao atualizar localizadores ou cookies.
- `debug/`: amostras fixas de API referenciadas no texto do TCC. Mantenha-as intactas para que o trabalho possa citar respostas conhecidas.
- `local/`: planilhas (`BD_alerta de voos com milhas.*`) onde ficam as séries históricas usadas para aferir se o preço atual está descontado ou acima do padrão.

## Notas de Contribuição
Mantenha as mudanças mínimas e bem documentadas—toda alteração precisa ser referenciada no texto final. Use commits curtos e no imperativo (por exemplo, “Atualizar headers da Smiles”) e informe se a mudança impacta milhas, dinheiro ou ambos. Pull requests devem incluir o comando utilizado para reproduzir a amostra de dados e, quando aplicável, anexar o JSON resultante para que os revisores confirmem o processo de extração. Não são necessários testes automatizados; apenas verifique manualmente se o script continua registrando o resumo das tarifas antes de abrir o PR.

## Estilo de Código
- Priorize soluções diretas e legíveis, sem camadas extras ou fallbacks complexos.
- Atenda aos pedidos de funções simples com implementações igualmente simples (`def funcao(a, b): return a / b`), sem adições ou proteções não solicitadas.
