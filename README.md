## 🏬 Distribuidora Vetor — ETL + API REST (Desafio Primora)

Projeto do desafio Primora (Bolsa Futuro Digital), em duas partes:

1. **Parte 1 — ETL:** lê a base de clientes (CSV), normaliza bairro, CEP, CNPJ, telefone, data e e-mail,
   enriquece com ViaCEP/BrasilAPI (com cache local), grava no banco e registra uma trilha de auditoria
   (valor original → valor tratado → critério/fonte).
2. **Parte 2 — API REST em Django (DRF):** consulta pública (GET) e operações restritas a usuários
   autenticados (token), com documentação OpenAPI em Redoc.

## Escopo do desafio — Parte 1 (ETL)

### Entregáveis esperados

| Entregável esperado | Como foi atendido | Onde está |
|---|---|---|
| Pipeline de ETL (Python) com etapas claras de extração, transformação e carga | Três etapas separadas (`extrair`, `transformar`, `carregar_no_banco`), executadas por `python manage.py rodar_etl` | `etl/pipeline.py`, `clientes/etl_service.py` |
| Base final tratada, persistida em banco SQL | Clientes e vendedores no PostgreSQL (ou SQLite) | Tabelas `clientes_cliente` e `clientes_vendedor` |
| Tabela ou log de auditoria: valor original → valor tratado → critério/fonte da decisão | Uma linha por alteração ou critério diferente de "ok"; também exportada em CSV com `--saida` | Tabela `clientes_auditoria` (admin) e `saida/auditoria_tratamento.csv` |
| Testes automatizados da lógica de normalização (chamadas externas simuladas, não reais) | 121 testes; ViaCEP e BrasilAPI simuladas, sem rede | `tests/` (`pytest`) |
| Documentação técnica explicando as regras adotadas e seus limites conhecidos | Regras por campo, critério de divergência, limites e o que foi verificado | [docs/DOCUMENTACAO_TECNICA.md](docs/DOCUMENTACAO_TECNICA.md) |
| Relatório curto (1-2 páginas) com os trade-offs: o que foi automatizado, o que foi tratado manualmente, e por quê | Cerca de 800 palavras, com os números da execução real | [docs/RELATORIO_TRADEOFFS.md](docs/RELATORIO_TRADEOFFS.md) |

### 🔴 Abordagens sugeridas e soluções adotadas

As abordagens apresentadas no enunciado foram utilizadas como referência para o desenvolvimento do projeto, considerando os requisitos técnicos e as necessidades de tratamento dos dados.

| **Abordagem possível** | **Solução adotada** | **Implementação** |
|---|---|---|
| Normalização textual determinística (caixa, acentuação, espaços e conteúdo entre parênteses) | Padronização dos textos em minúsculas, sem acentos, parênteses, sufixo "DF" e pontuação, permitindo identificar diferentes grafias de um mesmo bairro. | `etl/normalizers.py` (`chave_texto`) |
| Dicionário de correspondência (variante → nome canônico) | Utilização de um dicionário CSV para relacionar diferentes grafias aos nomes padronizados dos bairros, incluindo "Areal" e "Setor Habitacional Vicente Pires". | `etl/dicionario_bairros.csv` |
| Enriquecimento por APIs públicas de CEP (ViaCEP e BrasilAPI) | Integração com o ViaCEP como fonte principal e BrasilAPI como alternativa, utilizando cache local em SQLite para reduzir requisições. CEPs inexistentes são armazenados em cache, enquanto falhas de conexão não são armazenadas. | `etl/cep_client.py` |
| Tratamento de divergências entre o bairro informado e o retornado pela consulta de CEP | Priorização das informações retornadas pela API, com registro das divergências na auditoria. Quando não há confirmação pela API, utiliza-se o bairro informado após a normalização. | `etl/resolucao.py` e documentação técnica (seção 3.3) |
| Tratamento de dados inconsistentes (telefone, CNPJ, datas e e-mail) | Padronização dos telefones no formato E.164, formatação e validação de CNPJ, tratamento de datas em quatro formatos e validação de e-mails. Valores inválidos são sinalizados para análise, sem descarte automático dos registros. | `etl/normalizers.py` |

As regras de negócio utilizadas no projeto, incluindo a interpretação de datas ambíguas no formato `dd/mm` e o armazenamento das subdivisões dos bairros em campos específicos, estão detalhadas na documentação técnica, juntamente com os critérios de decisão, as limitações identificadas e os procedimentos de tratamento dos dados.

## Escopo do desafio — Parte 2 (API)

| Item | Onde está |
|---|---|
| CRUD de clientes e vendedores, rotas por bairro e por vendedor | `clientes/views.py`, `config/urls.py` |
| Autenticação por token e controle de acesso (logado: CRUD; não logado: só GET) | `POST /api/auth/token/` |
| Documentação da API (OpenAPI/Redoc) | `/api/docs/`, `/api/schema/` e, sem servidor, [docs/api.html](docs/api.html) |
| Admin com todas as tabelas | `clientes/admin.py` |
| Migrações | `clientes/migrations/` |
| Modelo de dados (MER + DER) | [docs/MODELO_DE_DADOS.md](docs/MODELO_DE_DADOS.md) |
| README | Este arquivo |

## Requisitos

- Python 3.10 ou mais novo (Django 6 exige 3.12+; em versões anteriores o pip instala o Django 5.2)
- PostgreSQL (opcional: sem configuração, o projeto usa SQLite, no arquivo `vetor.db`)

## 🛠 Instalação

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows (PowerShell)
source .venv/bin/activate           # Linux/macOS

# 2. Instalar os pacotes
pip install -r requirements.txt

# 3. Configurar o ambiente: copie .env.example para .env e informe a senha do PostgreSQL
#    (se DB_NAME não estiver no .env, o projeto usa SQLite no arquivo vetor.db)
copy .env.example .env              # Windows   |   cp .env.example .env   # Linux/macOS

# 4. Criar as tabelas
python manage.py migrate

# 5. Rodar o ETL (carrega clientes, vendedores e auditoria)
python manage.py rodar_etl                 # com consulta de CEP (internet)
python manage.py rodar_etl --sem-api       # offline, só com o dicionário de bairros
python manage.py rodar_etl --saida saida   # além do banco, exporta clientes e auditoria em CSV

# 6. Criar um usuário (admin e escrita na API)
python manage.py createsuperuser

# 6.1 Observação Importante

Utilize os procedimentos abaixo caso ocorra um erro ao criar o usuário **admin** (necessário para acesso administrativo e gravação na API).

## Exemplo de erro

Se a seguinte mensagem for exibida:

Usuário (leave blank to use 'halli'): admin

Error: That username is already taken.

Isso significa que o usuário **admin** já existe no banco de dados.

## Verificando a senha do usuário existente

Acesse o shell do Django:

python manage.py shell

Quando o prompt >>> for exibido, execute:

from django.contrib.auth.models import User

u = User.objects.get(username="admin")

u.check\_password("projeto123")

O resultado será:

- True → a senha é projeto123;
- False → a senha é diferente de projeto123.

---

# 6.2 Redefinir a senha do usuário admin

Caso a senha não seja conhecida ou esteja incorreta, execute:

python manage.py changepassword admin

O Django solicitará:

Changing password for user 'admin'

Password:

Password (again):

Digite a nova senha e confirme\-a quando solicitado.

Após a alteração, utilize a nova senha para acessar o painel administrativo e os recursos que dependem do usuário **admin**.

==> Você também pode verificar todos os usuários cadastrados:

python manage.py shell

from django.contrib.auth.models import User
print(list(User.objects.values('id', 'username', 'is_staff', 'is_superuser')))

Se o retorno vier vazio ([]), não existe nenhum usuário cadastrado no banco.
```

O ETL é idempotente: pode ser reexecutado sem duplicar dados e não apaga clientes criados pela API.
O arquivo `.env` guarda a senha e **não vai para o Git** (está no `.gitignore`).

## Rodar pelo VS Code

O projeto traz a pasta `.vscode` com as configurações prontas.

1. Abra a pasta do projeto (a que contém o `manage.py`) em *Arquivo → Abrir Pasta*.
2. Escolha o interpretador: `Ctrl+Shift+P` → *Python: Select Interpreter* → o do ambiente virtual onde você
   instalou os pacotes (termina em `.venv\Scripts\python.exe`). Se ele não aparecer na lista, use *Enter interpreter path...*.
3. Para rodar o ETL etapa por etapa: abra `executar_etl.py` e clique em **Run Python File** (▶), ou use **F5**.
   Ele mostra a extração, a transformação e a carga, uma de cada vez, e depois o resumo.
4. Em **Executar e Depurar** (`Ctrl+Shift+D`) há uma configuração para cada tarefa:

| Configuração | O que faz |
|---|---|
| ETL - 3 etapas (com API de CEP) | `executar_etl.py`, consultando ViaCEP/BrasilAPI |
| ETL - 3 etapas (offline, sem API) | `executar_etl.py --sem-api` |
| ETL - comando Django (rodar_etl + CSV) | `manage.py rodar_etl --saida saida` |
| Banco - migrate | `manage.py migrate` |
| API - runserver | Sobe a API em http://127.0.0.1:8000 |
| Testes - pytest | Roda os testes |

Os testes também aparecem no painel **Testing** do VS Code. Antes do primeiro ETL, rode a configuração
*Banco - migrate* (ou `python manage.py migrate`).

## Banco SQLite (arquivo vetor.db)

Sem `DB_NAME` no `.env`, o projeto grava no arquivo `vetor.db`, na pasta do projeto, sem precisar de servidor.
Para gerar o `vetor.db` mesmo com o PostgreSQL configurado no `.env`, force o SQLite só naquele terminal:

```powershell
$env:DB_ENGINE="sqlite"
python manage.py migrate
python manage.py rodar_etl --saida saida
```

As tabelas do projeto são `clientes_cliente`, `clientes_vendedor` e `clientes_auditoria`, além das tabelas
do próprio Django (usuários, tokens e sessões). O arquivo `vetor.db` não vai para o Git (está no `.gitignore`).
Para ver o conteúdo:

```powershell
python -c "import sqlite3; c=sqlite3.connect('vetor.db'); print(c.execute('SELECT bairro_normalizado, COUNT(*) FROM clientes_cliente GROUP BY 1').fetchall())"
```

## Consultar o Banco no VS Code

Ao abrir a pasta, o VS Code sugere instalar as extensões recomendadas (`.vscode/extensions.json`). O arquivo
[consultas.sql](consultas.sql) traz 9 consultas prontas (bairros agrupados, auditoria, divergências, vendedores).

**SQLite (arquivo `vetor.db`, o mais simples):**

1. Gere o arquivo: `$env:DB_ENGINE="sqlite"`, depois `python manage.py migrate` e `python manage.py rodar_etl`.
2. Instale a extensão **SQLite** (alexcvzz) e use `Ctrl+Shift+P` → *SQLite: Open Database* → escolha `vetor.db`.
   O painel **SQLITE EXPLORER** passa a listar o banco e as tabelas. Para consultar: abra `consultas.sql`,
   selecione uma consulta e use botão direito → *Run Selected Query*.
3. Para só ver as tabelas, a extensão **SQLite Viewer** (qwtel) abre o `vetor.db` com um clique.

**PostgreSQL (banco `vetor`):** instale **SQLTools** e **SQLTools PostgreSQL/Cockroach Driver**. A conexão
`vetor (PostgreSQL)` já está configurada em `.vscode/settings.json` e pede a senha ao conectar (ela não fica
salva no arquivo). Conecte pelo ícone do SQLTools na barra lateral e rode as consultas com `Ctrl+E Ctrl+E`.

As tabelas do projeto são `clientes_cliente`, `clientes_vendedor` e `clientes_auditoria`.

## Interface web (front end)

Com o servidor ligado, abra **http://127.0.0.1:8000/**. A interface usa só a API do projeto:

| Tela | O que faz | API usada |
|---|---|---|
| Painel | Total de clientes, faixa com a proporção por bairro e clientes por vendedor | `/api/clientes/bairros/`, `/api/clientes/`, `/api/vendedores/` |
| Clientes | Busca, filtro por bairro e por vendedor, detalhes | `/api/clientes/bairro/{nome}/`, `/api/clientes/vendedor/{id}/` |
| Vendedores | Lista com a quantidade de clientes de cada um | `/api/vendedores/` |

Sem login a interface é somente leitura (só GET). Ao clicar em **Entrar para editar**, ela pede usuário e senha, obtém o
token em `/api/auth/token/` e libera criar, editar e excluir clientes e vendedores. O arquivo da interface é
`clientes/templates/app.html` (HTML, CSS e JavaScript em um só arquivo, sem etapa de build).

## Rodar o servidor

```bash
python manage.py runserver
```

| Endereço | O que é |
|---|---|
| http://127.0.0.1:8000/ | Interface web (painel, clientes e vendedores) |
| http://127.0.0.1:8000/api/docs/ | Documentação interativa (Redoc, arquivos locais) |
| http://127.0.0.1:8000/api/swagger/ | Mesma documentação em Swagger UI (alternativa) |
| http://127.0.0.1:8000/api/schema/ | Schema OpenAPI (drf-spectacular) |
| http://127.0.0.1:8000/admin/ | Admin: Clientes, Vendedores e Auditoria |

A documentação também existe em arquivo único, que abre com duplo clique e **sem servidor**: [docs/api.html](docs/api.html) (schema em [docs/openapi.yaml](docs/openapi.yaml)). Para regenerá-la depois de mudar a API: `python manage.py gerar_docs_api`.

## Endpoints

| Método e rota | Descrição | Acesso |
|---|---|---|
| `GET/POST /api/clientes/` | Listar / criar clientes | GET público, POST autenticado |
| `GET/PUT/PATCH/DELETE /api/clientes/{id}/` | Detalhar, editar, excluir | GET público, demais autenticados |
| `GET /api/clientes/bairro/{nome}/` | Clientes de um bairro (aceita variações: `aguas claras`) | Público |
| `GET /api/clientes/bairros/` | Total de clientes por bairro normalizado | Público |
| `GET /api/clientes/vendedor/{id}/` | Clientes de um vendedor | Público |
| `GET/POST /api/vendedores/` | Listar / criar vendedores | GET público, POST autenticado |
| `GET/PUT/PATCH/DELETE /api/vendedores/{id}/` | Detalhar, editar, excluir | GET público, demais autenticados |
| `GET /api/vendedores/{id}/clientes/` | Clientes de um vendedor | Público |
| `POST /api/auth/token/` | Obter token (`username` e `password`) | Público |

A auditoria não é exposta na API, só no admin. As listas são paginadas (50 por página).

### Autenticação

```powershell
# PowerShell: obter o token e criar um cliente (id_cliente é gerado se omitido)
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/token/ `
     -ContentType "application/json" -Body '{"username":"admin","password":"SUA_SENHA"}'
$h = @{ Authorization = "Token $($r.token)" }
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/clientes/ -Headers $h `
     -ContentType "application/json" `
     -Body '{"razao_social":"Loja Nova","vendedor_id":1,"bairro_normalizado":"aguas claras"}'
```

```bash
# curl  ==> No PowerShell
$body = @{
    username = "admin"
    password = "SUA_SENHA"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/auth/token/" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Na criação e edição, CNPJ, telefone, CEP e bairro passam pelas mesmas normalizações do ETL
(CNPJ `XX.XXX.XXX/XXXX-XX`, telefone E.164, CEP `NNNNN-NNN`, bairro canônico). Um vendedor com
clientes vinculados não pode ser excluído (resposta 409).

## Testes

```bash
pytest
```

121 testes (ETL e API). Não usam rede (as APIs de CEP são simuladas) e rodam em SQLite.

## Estrutura

```
executar_etl.py    ETL etapa por etapa (roda direto no VS Code)
consultas.sql      consultas prontas (SQLite e PostgreSQL)
config/            configurações e urls
clientes/          modelos, serializers, views (API), admin, carga do ETL, comando rodar_etl, interface web (templates/app.html)
etl/               normalização, consulta de CEP com cache, regras de decisão, dicionário de bairros
data/              base de clientes (CSV)
tests/             testes do ETL e da API
.vscode/           configurações do VS Code (executar, depurar e testar)
docs/              MER + DER, documentação técnica do ETL, relatório de trade-offs
```

## Problemas comuns

- **Erro ao conectar no PostgreSQL (Windows):** quase sempre é senha ou usuário incorretos no `.env`. O projeto
  mostra a mensagem real do servidor (por exemplo, "autenticação do tipo senha falhou"). Confira `DB_PASSWORD`
  e salve o arquivo.
- **`/api/docs/` em branco:** a página precisa dos arquivos estáticos do Redoc. Rode `python -m pip install -r requirements.txt`
  (inclui `drf-spectacular-sidecar`), reinicie o servidor e use `Ctrl+F5` no navegador. A alternativa é `/api/swagger/`.
- **`No module named ...`:** o ambiente virtual não está ativo ou os pacotes não foram instalados.
- **`manage.py` não encontrado:** execute os comandos dentro da pasta do projeto.


## 🖥️ Evidências de execução no VS Code

Esta seção apresenta as evidências de funcionamento do projeto **Distribuidora Vetor**, incluindo a execução do pipeline ETL, a validação dos dados no PostgreSQL, a auditoria das transformações e os testes automatizados.

### 1. Execução do pipeline ETL

✅ O pipeline realiza as etapas de **extração, transformação e carga (ETL)**, processando os dados dos clientes e persistindo as informações tratadas no PostgreSQL.

**Comando executado no terminal:**

```powershell
python executar_etl.py
```

**Evidência da execução:**

<img width="1349" height="758" alt="Execução do pipeline ETL" src="https://github.com/user-attachments/assets/65248e62-afab-4cdf-8d28-2cace37374b7" />

### 2. Resumo do processamento

✅ O ETL processou **47 clientes**, normalizou os registros em quatro bairros canônicos, gerou **194 registros de auditoria** e identificou um registro para revisão manual.

O processamento também identificou divergências entre informações fornecidas no CSV e dados retornados pela API de CEP.

**Comando executado:**

```powershell
python executar_etl.py
```

**Evidência do resumo gerado pelo ETL:**

<img width="1351" height="756" alt="Resumo do processamento ETL" src="https://github.com/user-attachments/assets/744ea4d4-59d9-4efa-a537-6910c86e31d6" />

### 3. Normalização dos bairros

✅ A consulta SQL verifica a distribuição dos clientes por bairro após a normalização e confirma que os dados tratados foram armazenados no PostgreSQL.

**Consulta SQL:**

```sql
SELECT
    COALESCE(bairro_normalizado, 'Sem bairro') AS bairro,
    COUNT(*) AS total_clientes
FROM clientes_cliente
GROUP BY bairro_normalizado
ORDER BY total_clientes DESC;
```

**Resultado obtido:**

| Bairro | Clientes |
|---|---:|
| Águas Claras | 21 |
| Taguatinga | 11 |
| Vicente Pires | 8 |
| Guará | 6 |
| Sem bairro | 1 |
| **Total** | **47** |

**Evidência da consulta:**

<img width="1395" height="754" alt="Consulta SQL de clientes por bairro" src="https://github.com/user-attachments/assets/2e84d777-34cf-4ac9-a5e4-0e020d64674a" />

### 4. Relacionamento entre clientes e vendedores

✅ A consulta utiliza `LEFT JOIN` para verificar o relacionamento entre as tabelas de clientes e vendedores, apresentando a quantidade de clientes vinculados a cada vendedor.

**Consulta SQL:**

```sql
SELECT
    v.nome_vendedor,
    COUNT(c.id_cliente) AS total_clientes
FROM clientes_vendedor v
LEFT JOIN clientes_cliente c
    ON c.vendedor_id = v.id_vendedor
GROUP BY v.id_vendedor, v.nome_vendedor
ORDER BY total_clientes DESC;
```

**Resultado obtido:**

| Vendedor | Clientes |
|---|---:|
| Camila Torres | 14 |
| Diego Martins | 11 |
| Bruno Almeida | 10 |
| Juliana Reis | 9 |
| Rafael Souza | 3 |
| **Total** | **47** |

**Evidência da consulta:**

<img width="1359" height="756" alt="Consulta SQL de clientes por vendedor" src="https://github.com/user-attachments/assets/250811cc-597f-427d-bd0c-b200d3a4fb22" />

### 5. Auditoria das transformações

✅ O sistema registra os valores originais, os valores tratados e os critérios aplicados durante a execução do ETL, permitindo rastrear as alterações realizadas nos dados.

**Consulta para verificar a quantidade de registros:**

```sql
SELECT COUNT(*) AS total_auditorias
FROM clientes_auditoria;
```

**Consulta para visualizar os registros de auditoria:**

```sql
SELECT
    cliente_id,
    campo,
    valor_original,
    valor_tratado,
    criterio
FROM clientes_auditoria
ORDER BY cliente_id, campo
LIMIT 5;
```

**Resultado:** 194 registros de auditoria armazenados no PostgreSQL.

**Evidência da auditoria:**

<img width="1409" height="758" alt="Consulta SQL dos registros de auditoria" src="https://github.com/user-attachments/assets/dd9ec8c5-b2ae-40a7-930d-b53e88975343" />

### 6. Tratamento de divergências

✅ O cliente `CLI0002` apresentou divergência entre o bairro informado no arquivo CSV e o bairro retornado pela consulta de CEP.

O sistema priorizou o retorno da API ViaCEP e registrou o critério utilizado na tabela de auditoria, garantindo a rastreabilidade da decisão.

**Consulta SQL:**

```sql
SELECT
    campo,
    valor_original,
    valor_tratado,
    criterio
FROM clientes_auditoria
WHERE cliente_id = 'CLI0002'
  AND campo = 'bairro';
```

**Resultado obtido:**

| Informação | Valor |
|---|---|
| Cliente | CLI0002 |
| Bairro original | Sul (Aguas Claras) |
| Bairro tratado | Taguatinga / Norte |
| Critério | `divergencia_api_prevalece` |
| Fonte | ViaCEP |

**Evidência do tratamento da divergência:**

<img width="1344" height="756" alt="Consulta SQL da divergência de bairro do cliente CLI0002" src="https://github.com/user-attachments/assets/ea9d20f8-bafb-4ffb-b558-e88fd6fcfd16" />

### 7. Testes automatizados

✅ Os testes automatizados foram executados com **Pytest**, verificando as regras de tratamento dos dados e o funcionamento dos recursos implementados.

**Comando executado:**

```powershell
python -m pytest -q
```

**Resultado obtido:**

```text
121 passed in 39.29s
```

Todos os **121 testes foram aprovados** na execução realizada.

**Evidência dos testes:**

<img width="1355" height="753" alt="Resultado dos testes automatizados com Pytest" src="https://github.com/user-attachments/assets/6151dbb1-1977-4094-b5a4-1536267af200" />

---

### Observação sobre a execução das consultas SQL

As consultas SQL apresentadas foram executadas no PostgreSQL por meio do shell do Django, utilizando a conexão configurada no projeto.

**Para acessar o shell:**

```powershell
python manage.py shell
```

**Para importar a conexão:**

```python
from django.db import connection
```

**Exemplo de execução de uma consulta:**

```python
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COUNT(*)
        FROM clientes_auditoria;
    """)
    print(cursor.fetchone())
```

Esse procedimento permite executar consultas SQL diretamente pelo Django, sem a necessidade de utilizar o programa `psql` no terminal do Windows.


## 📸 Demonstração do Sistema

### ==> Painel Principal

✅ O painel apresenta os 47 clientes distribuídos em quatro bairros normalizados, além de um cliente sem bairro.

<img width="1353" height="697" alt="Painel principal" src="https://github.com/user-attachments/assets/736e574f-fe47-4b74-bef1-9ec6c37f78a7" />

### ==> Listagem de Clientes

✅ A interface apresenta os clientes com razão social, bairro, vendedor, CNPJ e telefone padronizados.

<img width="1376" height="728" alt="Listagem de clientes" src="https://github.com/user-attachments/assets/bb1d90c1-8f4d-46c0-8f3d-6cb8ec1592f4" />

### ==> Vendedores

✅ A tela apresenta os cinco vendedores e a quantidade de clientes vinculados a cada um.

<img width="1364" height="723" alt="vendedores" src="https://github.com/user-attachments/assets/5b43eb8b-e848-4d1f-81d7-f869aadc3a4c" />

### ==> Filtro por Vendedor

✅ Ao selecionar Camila Torres, o sistema apresenta os 14 clientes vinculados à vendedora.

<img width="1348" height="730" alt="Ao selecionar Camila Torres" src="https://github.com/user-attachments/assets/3fa0be68-da03-48ba-b41b-f67608d63b32" />



## 👥 Autoria
- Autores: Aleandreson, Hallison, Bruno Miranda e Cecília
- Projeto: Desafio Primora
- Área: Desenvolvimento de Software BackEnd - Python com Django
- Instituição: Instituto Federal de Brasília (IFB)
  
