# 3. Metodologia e Técnicas da Pesquisa (Foco em Web Scraping)

Este capítulo descreve, de forma detalhada e progressiva, a metodologia de coleta automatizada de dados (web scraping) empregada para obter preços de passagens aéreas em dinheiro e em milhas nos programas e sites da Azul e da Smiles. A opção metodológica central foi extrair dados diretamente dos endpoints públicos que alimentam as páginas dessas plataformas, evitando a raspagem de HTML. Essa estratégia aumenta a precisão, reduz a fragilidade a mudanças cosméticas e facilita a reprodutibilidade.

Os resultados dessa coleta alimentam o restante do estudo (comparação milhas vs. dinheiro e comparação com faixa histórica), mas aqui tratamos exclusivamente da técnica de scraping: descoberta de endpoints, replicação controlada das requisições, mitigação de anti‑bot, e persistência do JSON bruto para análise posterior.

---

## 3.1 Desenho Metodológico do Scraping

- Abordagem por endpoints: em vez de navegar e selecionar elementos HTML, abrimos o site real em um navegador automatizado apenas para observar e registrar as chamadas de rede (Network) que os sites fazem para suas próprias APIs. Em seguida, reproduzimos essas chamadas via HTTP programático.
- Captura de contexto de rede: coletamos cabeçalhos, cookies e, quando necessário, o corpo do POST a partir de uma sessão real no navegador. Isso fornece o “molde” mínimo para replicar a consulta.
- Execução controlada: utilizamos um cliente HTTP com impersonação de navegador (TLS/JA3 e cabeçalhos) para reduzir falsos positivos de bloqueio e obter respostas idênticas às do site.
- Persistência fidedigna: salvamos o payload JSON bruto em disco para auditoria, versionamento e reuso em planilhas/notebooks externos. Pequenos resumos (menores tarifas de ida e volta) são calculados de forma auxiliar, sem alterar o JSON original.

Justificativa técnica: endpoints REST/JSON são mais estáveis em estrutura do que HTML exibido ao usuário. Ao mapear as chamadas e reproduzi‑las com o mínimo indispensável de cabeçalhos/cookies, a coleta torna‑se mais resiliente, transparente e auditável.

---

## 3.2 Ferramental, Ambiente e Ética

- Linguagem e bibliotecas: Python 3.x; `curl_cffi.requests` (HTTP com impersonação), `selenium-driverless` (observer de rede), `arrow` (datas), `rich` (logs). O Playwright é usado apenas para inspeção manual (não no pipeline automatizado).
- Execução local: os scripts rodam localmente, escrevendo os JSONs em diretórios do repositório (`smiles_output/` e equivalentes para a Azul). O banco histórico vive em `local/` e é tratado por planilhas/notebooks fora do escopo desta seção.
- Ética e conformidade: coletamos apenas dados públicos, respeitando limites razoáveis de frequência (pequenos `sleep`s), sem burlar paywalls. Endpoints e cookies se alteram com o tempo; sempre há uma etapa humana de verificação quando detectamos mudança estrutural. Não capturamos credenciais pessoais.

Placeholders de execução (para pontos do texto onde blocos de código não cabem):
- [EXECUTAR] `python smiles_scraper/smiles_scraper_interceptor.py` (raspagem Smiles)
- [EXECUTAR] `python azul_scraper/azul_scraper_api_money.py` (Azul em reais)
- [EXECUTAR] `python azul_scraper/azul_scraper_api_miles.py` (Azul em pontos)

---

## 3.3 Descoberta dos Endpoints via Network

A etapa inicial consiste em reproduzir manualmente uma busca (origem, destino, datas) no site e observar, na aba Network do navegador, quais requisições são disparadas para obter os resultados. Em vez de “adivinhar” os parâmetros, interceptamos exatamente o que o site envia e recebe.

Exemplos (observáveis no navegador e usados como referência):
- Smiles (GET): `https://api-air-flightsearch-*.smiles.com.br/v1/airlines/search?...`
- Azul (POST em reais): `https://b2c-api.voeazul.com.br/reservationavailability/api/reservation/availability/v5/availability`
- Azul (POST em pontos): `https://b2c-api.voeazul.com.br/tudoAzulReservationAvailability/api/tudoazul/reservation/availability/v5/availability`

Para capturar esse contexto de rede programaticamente, abrimos o site com parâmetros de busca e usamos um interceptor de requisições. O objetivo aqui não é “raspar” a página, mas apenas observar a chamada legítima da própria aplicação.

Snippet (abrir a página da Smiles com parâmetros e interceptar cookies/cabeçalhos):
```python
# smiles_scraper/smiles_scraper_interceptor.py: SmilesFlightSearch._on_request (trecho)
if "smiles.com.br" in data.request.url and data.request.headers:
    cookie_value = next(
        (v for k, v in data.request.headers.items() if k.lower() == "cookie"), None
    )
    if cookie_value and ("bm_sz=" in cookie_value or "_abck=" in cookie_value):
        self.requests_headers = data.request.headers
        self.requests_cookies = cookie_value
```

---

## 3.4 Replicação Programática das Requisições

Uma vez capturados cookies/cabeçalhos/corpos necessários, replicamos a chamada HTTP no Python. Preferimos `curl_cffi.requests` com o parâmetro `impersonate` para emular perfis reais de navegador (reduzindo bloqueios por fingerprinting de TLS/JA3).

### 3.4.1 Smiles (GET com cookies e cabeçalhos)

A Smiles reforça validações por cookie e user‑agent. O fluxo é: (1) abrir a página de busca (com datas em timestamp) para capturar cookies; (2) realizar um GET no endpoint de busca com os mesmos parâmetros do site.

Snippet (construção de headers e GET autenticado por cookies):
```python
# smiles_scraper/smiles_scraper_interceptor.py: SmilesFlightSearch.get_flight_info (trechos)
headers = {
    'accept': 'application/json, text/plain, */*',
    'origin': 'https://www.smiles.com.br',
    'referer': 'https://www.smiles.com.br/',
    'user-agent': self._get_intercepted_header('user-agent', 'Mozilla/5.0 ...'),
    'x-api-key': '...capturada do tráfego...'
}
# cookies_dict resulta do filtro dos cookies efetivamente usados pelo endpoint
resp = requests.get(
    url="https://api-air-flightsearch-...smiles.com.br/v1/airlines/search",
    params=params, headers=headers, cookies=cookies_dict, impersonate="chrome120",
)
raw = resp.json()
```

Extração de um resumo objetivo (menores valores de ida/volta):
```python
# smiles_scraper/smiles_scraper_interceptor.py: extract_flight_info (trecho)
segments = raw["requestedFlightSegmentList"]
out = segments[0].get("bestPricing", {})
in_ = segments[1].get("bestPricing", {})
sumario = {
    "lowest_outbound_miles": out.get("miles"),
    "lowest_outbound_money": out.get("money"),
    "lowest_inbound_miles": in_.get("miles"),
    "lowest_inbound_money": in_.get("money"),
}
```

Persistência do JSON bruto (traço metodológico importante):
```python
# exemplo didático de persistência
from pathlib import Path, PurePath
import json, time

output_dir = Path("smiles_output")
output_dir.mkdir(exist_ok=True)
fname = f"{origin}_{destination}_{departure_date}_{return_date}_{int(time.time())}.json"
with (output_dir / fname).open("w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False)
```

Placeholder de execução:
- [EXECUTAR] `python smiles_scraper/smiles_scraper_interceptor.py`

### 3.4.2 Azul em Reais (POST com corpo interceptado)

Para a Azul (preço em BRL), o site envia um POST contendo um corpo JSON relativamente rico (com chaves como `criteria` ou `trips`). O passo chave é interceptar esse corpo e os cabeçalhos correspondentes uma única vez, e depois apenas atualizar as datas para reexecutar a pesquisa.

Captura do corpo e headers via interceptor:
```python
# azul_scraper/azul_scraper_api_money.py: FlightSearchMoney._on_request (trecho)
if (
    ".../reservation/availability/v5/availability" in data.request.url
    and data.request.method == "POST"
):
    self.requests_headers = data.request.headers
    self.requests_body_template = json.loads(data.request.post_data)
```

Atualização mínima do corpo para novas datas e sentidos:
```python
# azul_scraper/azul_scraper_api_money.py: _update_request_body (trecho)
body = json.loads(json.dumps(self.requests_body_template))
body["criteria"][0].update({
    "departureStation": origin,
    "arrivalStation": destination,
    "std": departure_date,            # MM/DD/YYYY
    "departureDate": dep_date_api,    # YYYY-MM-DD
})
body["criteria"][1].update({
    "departureStation": destination,
    "arrivalStation": origin,
    "std": return_date,
    "departureDate": ret_date_api,
})
```

Execução do POST com impersonação e parsing do menor valor:
```python
resp = requests.post(
    url="https://b2c-api.voeazul.com.br/reservationavailability/api/reservation/availability/v5/availability",
    headers=self.requests_headers, json=body, impersonate="chrome123",
)
raw = resp.json()
lowest = raw["data"]["trips"][0]["fareInformation"]["lowestAmount"]
```

Placeholder de execução:
- [EXECUTAR] `python azul_scraper/azul_scraper_api_money.py`

### 3.4.3 Azul em Pontos (POST TudoAzul)

O fluxo é idêntico ao de reais, porém com outro endpoint e interpretação de campos (pontos em vez de reais). O seletor de canal (`cc=PTS`) é usado na URL de abertura da página apenas para induzir o front‑end a chamar o endpoint correto, que então interceptamos.

Trechos relevantes:
```python
# azul_scraper/azul_scraper_api_miles.py
if ".../tudoazul/reservation/availability/v6/availability" in data.request.url:
    self.requests_headers = data.request.headers
    self.requests_body_template = json.loads(data.request.post_data)

resp = requests.post(
    url="https://b2c-api.voeazul.com.br/tudoAzulReservationAvailability/api/tudoazul/reservation/availability/v5/availability",
    headers=self.requests_headers, json=updated_body, impersonate="chrome123",
)
```

Extração do menor total em pontos:
```python
trips = raw["data"]["trips"]
lowest_out = trips[0]["fareInformation"]["lowestPoints"]
lowest_in  = trips[1]["fareInformation"]["lowestPoints"]
```

Placeholder de execução:
- [EXECUTAR] `python azul_scraper/azul_scraper_api_miles.py`

---

## 3.5 Estratégias de Robustez e Observabilidade

- Impersonação e cookies: `impersonate="chromeXXX"` em `curl_cffi.requests` e reuso de cookies e cabeçalhos reduz bloqueios por fingerprinting e validações anti‑bot. Em Smiles, a presença de chaves como `_abck`/`bm_sz` foi usada como heurística para “cookies bons”.
- Atrasos e limites: adicionamos pequenos `sleep`s entre consultas e não usamos concorrência agressiva. Isso diminui a chance de rate limiting e melhora a estabilidade dos dados coletados.
- Validações leves: cada etapa verifica a presença de chaves esperadas (`requestedFlightSegmentList`, `data.trips`, `fareInformation`). Quando ausentes, registramos a anomalia e persistimos o payload mesmo assim para investigação manual.
- Logs: usamos `rich.print` para mensagens claras de depuração e para relatar a origem dos cookies/headers interceptados e status de resposta dos endpoints.
- Observação manual: `azul_scraper_playwright.py` serve como “lupa” quando há mudança de layout/comportamento no front, permitindo re‑validar seletores e identificar novos parâmetros.

---

## 3.6 Amostragem e Agendamento (Somente Scraping)

O scraping foi planejado como coleta pontual e reexecutável sob demanda, com potencial de agenda semanal. Os parâmetros (origem, destino, ida e volta) podem ser iterados para formar o “grid” de busca.

Exemplo de pseudocódigo para varrer um pequeno conjunto (reais):
```python
rotas = [("BEL", "GRU"), ("SDU", "CGH")]
datas = [("11/30/2025", "12/02/2025")]
for (ori, des) in rotas:
    for (ida, volta) in datas:
        # [EXECUTAR] python azul_scraper/azul_scraper_api_money.py --origin %s --destination %s --departure %s --return %s
        pass
```

A persistência de todos os JSONs é mandatória para reprodutibilidade e auditoria. Cada execução deve registrar: origem, destino, datas (ida/volta), timestamp e canal (milhas vs. dinheiro).

---

## 3.7 Reprodutibilidade da Coleta

- Comandos de referência (incluir no PR ao anexar amostras):
  - Smiles: `python smiles_scraper/smiles_scraper_interceptor.py`
  - Azul (R$): `python azul_scraper/azul_scraper_api_money.py`
  - Azul (PTS): `python azul_scraper/azul_scraper_api_miles.py`
- Anexos esperados: arquivos JSON resultantes da execução, conforme gravados no diretório da companhia; um snippet de log com parâmetros e status code ajuda os revisores a confirmar a rota e as datas da requisição.

---

## 3.8 Limitações e Riscos (Técnica de Scraping)

- Fragilidade a mudanças de API: endpoints e corpos de requisição podem mudar de versão/estrutura. Mitigação: interceptação periódica (via driverless/Playwright) para atualizar templates e key‑paths.
- Cookies voláteis e anti‑bot: a Smiles pode invalidar cookies com rapidez; nesses casos, é preciso reabrir a página e recapturar antes de refazer o GET. O método `initialize_headers` incorpora essa etapa.
- Sazonalidade e volume: buscas em alta demanda podem introduzir respostas degradadas ou limites temporários. A execução cuidadosa (sem paralelismo agressivo) minimiza o impacto.

---

## 3.9 Conclusão (Delineamento do Scraping)

A metodologia de scraping adotada privilegia a rastreabilidade e a precisão: observamos o tráfego legítimo do front‑end, capturamos o contexto mínimo (cookies, cabeçalhos, corpos), e replicamos as chamadas com um cliente HTTP que emula um navegador real. O resultado é um pipeline simples e auditável que preserva o JSON integral e calcula resumos objetivos (menores tarifas de ida/volta), fornecendo insumos confiáveis para as etapas analíticas do TCC.

```text
[EXECUTAR] Coleta Smiles: python smiles_scraper/smiles_scraper_interceptor.py
[EXECUTAR] Coleta Azul R$: python azul_scraper/azul_scraper_api_money.py
[EXECUTAR] Coleta Azul PTS: python azul_scraper/azul_scraper_api_miles.py
```

> Nota final: as amostras em `debug/` permanecem como referenciais fixos e não devem ser alteradas, permitindo citar respostas conhecidas no corpo do trabalho.

