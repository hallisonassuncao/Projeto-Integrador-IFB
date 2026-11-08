# Documentação técnica — ETL da base de clientes (Distribuidora Vetor)

## 1. Visão geral

```
CSV (;) ──► extrair ──► transformar ──► carregar ──► PostgreSQL
                          │   ▲                         ├─ clientes_tratados
                          │   └── ClienteCep            └─ auditoria_tratamento
                          │       (ViaCEP → BrasilAPI,
                          │        cache SQLite local)
                          └─► dicionario_bairros.csv (variante → bairro canônico)
```

| Módulo | Responsabilidade |
|---|---|
| `etl/normalizers.py` | Funções puras de normalização (bairro, CEP, CNPJ, telefone, data, e-mail) |
| `etl/cep_client.py` | Consulta de CEP com fallback entre provedores e cache local |
| `etl/resolucao.py` | Critério explícito para combinar bairro informado × bairro da API |
| `etl/pipeline.py` | Extração, transformação, carga e resumo; define as tabelas |
| `etl/dicionario_bairros.csv` | Dicionário variante → bairro canônico (+ subdivisão), ampliável sem mexer em código |
| `main.py` | CLI |

## 2. Como executar

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/vetor
python main.py                      # com consulta de CEP (internet)
python main.py --sem-api --db-url sqlite:///vetor.db   # offline, sem PostgreSQL
pytest                              # 74 testes, sem rede e sem PostgreSQL
```

Saídas: tabelas no banco + `saida/clientes_tratados.csv` + `saida/auditoria_tratamento.csv`
+ resumo em JSON no terminal. A carga é uma **recarga completa e atômica** (uma transação):
reexecutar não duplica linhas.

## 3. Regras de tratamento

### 3.1 Bairro
1. **Chave textual**: minúsculas, sem acentos, sem parênteses, sem sufixo `DF`, pontuação vira espaço
   (`"Sul (Águas Claras)"` → `"sul aguas claras"`; `"Taguatinga - DF"` → `"taguatinga"`).
2. **Dicionário**: a chave é procurada em `dicionario_bairros.csv`, que devolve *bairro canônico* e
   *subdivisão*. Ex.: `sul aguas claras` → (`Águas Claras`, `Sul`); `vte pires` → (`Vicente Pires`, `—`).
3. **Fuzzy (rede de segurança)**: chave fora do dicionário, mas com similaridade ≥ 0,88 com uma entrada
   (`difflib`), é mapeada **e marcada para revisão manual** (`criterio = fuzzy`).
4. **Não mapeado**: bairro nulo, `revisao_manual = true`. Nada é inventado.

**Bairro-pai × subdivisão.** O relatório agrega pelo bairro-pai (`bairro`); a subdivisão informal
(Sul/Norte, I/II) fica em coluna própria (`subdivisao`) e não se perde.

### 3.2 CEP e enriquecimento
- CEP é padronizado para `NNNNN-NNN`. Vazio → `ausente`; tamanho errado ou todos os dígitos iguais
  (`00000-000`) → `invalido`. Só CEPs `ok` são consultados.
- Consulta: **ViaCEP** primeiro; se falhar (timeout, 5xx, JSON inválido) ou vier sem bairro, **BrasilAPI**.
- **Cache local** (SQLite, `cache/cep_cache.sqlite`): guarda acertos e também "CEP não existe"
  (cache negativo). **Falhas de rede nunca são cacheadas**, para não gravar um "não existe" falso.
- Resposta com UF diferente da do cadastro é **ignorada** e vai para revisão manual.
- O bairro devolvido pela API passa pelo mesmo normalizador/dicionário que o bairro informado.

### 3.3 Critério de divergência (bairro informado × API)

| Situação | Bairro final | Fonte | Flags |
|---|---|---|---|
| Sem resposta utilizável da API (CEP ausente/inválido, API fora do ar, CEP inexistente) | informado (se mapeado) | `informado` | — |
| Informado ausente ou não mapeado, API mapeada | API | `api_cep` | — |
| Ambos mapeados, mesmo bairro-pai | API; subdivisão = informada, senão a da API | `api_cep+informado` | — |
| Ambos mapeados, bairros-pai diferentes | **API prevalece** | `api_cep` | `divergencia_cep_bairro = true` |
| Bairro da API fora do dicionário | informado | `informado` | `revisao_manual = true` |

Justificativa: o CEP é uma fonte estruturada e verificável; o bairro é texto livre digitado por
vendedores. Em contrapartida, um CEP errado digitado com bairro certo seria "corrigido" para errado —
por isso a divergência é sempre sinalizada e auditada, nunca silenciosa.

### 3.4 Demais campos
| Campo | Regra | Não faz |
|---|---|---|
| CNPJ | Remove pontuação, exige 14 dígitos, formata `XX.XXX.XXX/XXXX-XX`, valida dígitos verificadores → `cnpj_dv_valido` | Não descarta CNPJ com DV inválido (ver §5) |
| Telefone | Remove `+55`/máscara; 10 dígitos = fixo (inicia 2–5), 11 = celular (inicia 9); DDD 11–99; saída E.164 `+55DDNNNNNNNNN` | Não adivinha dígito faltante |
| Data | ISO, `dd/mm/aaaa`, `dd-mm-aaaa` e `Mon d, aaaa` (meses em inglês/português abreviados); saída `DATE` | Não usa `locale` do SO |
| E-mail | trim + minúsculas + validação de formato (`email_valido`) | Não corrige o endereço |
| Razão social | Colapsa espaços | — |

**Premissa de negócio (assumida e documentada):** datas com `/` ou `-` são `dd/mm/aaaa`
(padrão brasileiro). Quando dia e mês são ambos ≤ 12 e diferentes, a leitura `mm/dd` mudaria a data;
esses casos recebem `data_ambigua = true` (no CSV fornecido: 6 registros).

## 4. Modelagem de Dados (MER, DDL e estrutura relacional)

O modelo descrito abaixo representa a **base final tratada e persistida em banco SQL**, resultado do processo de ETL. Ele não reflete o arquivo bruto de entrada em CSV, pois a tabela final inclui campos gerados durante a normalização e enriquecimento, como validações, indicadores de qualidade, bairro canônico e status de processamento.

O armazenamento utiliza uma estrutura relacional normalizada para garantir a persistência dos dados tratados do pipeline e a rastreabilidade das operações de ETL.

### 4.1. Modelo Conceitual (MER)
O modelo conceitual descreve as principais entidades identificadas no domínio do problema:

- **Vendedor:** representa os responsáveis comerciais do atendimento dos clientes.
- **Cliente (`clientes_tratados`):** entidade central que armazena o cadastro tratado e normalizado.
- **Auditoria (`auditoria_tratamento`):** entidade de suporte destinada a registrar o histórico detalhado de cada alteração aplicada aos campos do cliente.

Relacionamentos principais:
- Um **Vendedor** atende múltiplos **Clientes** (relação 1:N).
- Cada **Cliente** pode gerar múltiplas entradas na **Auditoria** (relação 1:N).
- Cada registro de auditoria está associado a um único cliente.

Para este desafio, o bairro foi tratado como atributo do cliente, em vez de uma entidade separada, porque a análise de domínio foi feita no contexto do cadastro e do tratamento do CEP. Isso mantém a simplicidade do modelo relacional sem perder a rastreabilidade.

![Modelo conceitual](./imagens/modeloconeitual.png)

### 4.2. Modelo Lógico e estrutura das tabelas
O modelo lógico define as tabelas, colunas, tipos de dados e restrições de integridade.

1. **`vendedores`**
   - `id_vendedor` (INTEGER, PK) — identificador único do vendedor.
   - `nome_vendedor` (VARCHAR) — nome completo do vendedor.

2. **`clientes_tratados`**
   - `id_cliente` (VARCHAR, PK) — identificador único do cliente.
   - `razao_social` (VARCHAR) — nome comercial do cliente.
   - `cnpj` (VARCHAR) / `cnpj_dv_valido` (BOOLEAN) — CNPJ tratado e validação do dígito verificador.
   - `telefone` (VARCHAR) / `telefone_tipo` (VARCHAR) — contato e tipo de linha.
   - `email` (VARCHAR) / `email_valido` (BOOLEAN) — endereço eletrônico tratado e validado.
   - `cep` (VARCHAR) / `cep_status` (VARCHAR) — CEP normalizado e estado de validação.
   - `bairro_informado` / `bairro` / `subdivisao` / `bairro_fonte` — dados geográficos originais e normalizados.
   - `divergencia_cep_bairro` (BOOLEAN) / `revisao_manual` (BOOLEAN) — flags de qualidade.
   - `cidade` (VARCHAR) / `uf` (VARCHAR) — dados de localização.
   - `data_cadastro` (DATE) / `data_ambigua` (BOOLEAN) — data tratada e sinalização de ambiguidade.
   - `vendedor_id` (INTEGER, FK) — referência ao vendedor responsável.

3. **`auditoria_tratamento`**
   - `id` (INTEGER, PK) — chave primária da auditoria.
   - `id_cliente` (VARCHAR, FK) — cliente afetado pela operação.
   - `campo` (VARCHAR) — atributo submetido ao tratamento.
   - `valor_original` (TEXT) — valor bruto original do CSV.
   - `valor_tratado` (TEXT) — valor final após normalização.
   - `criterio` (TEXT) — regra ou motivo da correção.
   - `fonte` (VARCHAR) — origem da decisão (`regra`, `informado`, `api_cep`).
   - `revisao_manual` (BOOLEAN) — indicador de necessidade de revisão humana.
   - `executado_em` (TIMESTAMPTZ) — timestamp da execução.

![Modelo lógico](./imagens/modelo_logico.png)

### 4.3. Estrutura física (DDL para PostgreSQL)
Código SQL para criação da base relacional:

```sql
CREATE TABLE vendedores (
    id_vendedor SERIAL PRIMARY KEY,
    nome_vendedor VARCHAR(100) NOT NULL
);

CREATE TABLE clientes_tratados (
    id_cliente VARCHAR(20) PRIMARY KEY,
    razao_social VARCHAR(200),
    cnpj VARCHAR(18),
    cnpj_dv_valido BOOLEAN,
    telefone VARCHAR(15),
    telefone_tipo VARCHAR(10),
    email VARCHAR(150),
    email_valido BOOLEAN,
    cep VARCHAR(9),
    cep_status VARCHAR(30),
    bairro_informado VARCHAR(100),
    bairro VARCHAR(100),
    subdivisao VARCHAR(30),
    bairro_fonte VARCHAR(30),
    divergencia_cep_bairro BOOLEAN,
    revisao_manual BOOLEAN,
    cidade VARCHAR(80),
    uf VARCHAR(2),
    data_cadastro DATE,
    data_ambigua BOOLEAN,
    vendedor_id INTEGER,
    CONSTRAINT fk_cliente_vendedor
        FOREIGN KEY (vendedor_id) REFERENCES vendedores(id_vendedor)
);

CREATE TABLE auditoria_tratamento (
    id SERIAL PRIMARY KEY,
    id_cliente VARCHAR(20) NOT NULL,
    campo VARCHAR(30),
    valor_original TEXT,
    valor_tratado TEXT,
    criterio TEXT,
    fonte VARCHAR(30),
    revisao_manual BOOLEAN,
    executado_em TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_auditoria_cliente
        FOREIGN KEY (id_cliente) REFERENCES clientes_tratados(id_cliente)
);
```

### 4.4. Justificativa da modelagem
- A tabela `clientes_tratados` armazena a versão final da base, pronta para consulta e análise.
- A tabela `auditoria_tratamento` preserva o histórico das transformações, permitindo rastrear cada decisão de limpeza.
- A separação entre dados finais e dados de auditoria evita perda de informação e aumenta a confiabilidade do processo.
- A tabela `vendedores` reduz redundância e mantém a integridade referencial.
- O uso de chaves estrangeiras garante que não existam registros órfãos e que a relação entre entidades seja consistente.

## 5. Limites conhecidos

1. **CNPJ**: nenhum dos 47 CNPJs da base passa na validação dos dígitos verificadores (base sintética).
   Rejeitá-los esvaziaria a tabela; por isso são padronizados e sinalizados. Em produção a regra deve
   ser revista (quarentena ou rejeição).
2. **Dicionário construído a partir desta amostra** (47 linhas): bairros fora dela cairão em
   `nao_mapeado`/`fuzzy` e exigirão revisão manual para entrar no dicionário.
3. **CEP em Brasília é pouco granular**: vários CEPs cobrem quadras/áreas amplas, e o nome de bairro
   devolvido pelas APIs pode ser genérico, vazio ou diferente do nome popular (ex.: "Setor ...").
   Nesses casos o pipeline mantém o informado e pede revisão, mas a **qualidade real das respostas
   de ViaCEP/BrasilAPI para estes CEPs não foi medida** (ver §6).
4. **Subdivisões** (Sul/Norte, I/II) são mantidas como informadas; não há fonte oficial no pipeline
   que as confirme.
5. **Datas ambíguas** seguem a premissa `dd/mm`; sem uma segunda fonte, não há como confirmar.
6. **Telefone**: valida formato e DDD, não se o número existe.
7. **Fuzzy** é heurístico: pode aproximar nomes de bairros diferentes e semelhantes — por isso sempre
   exige revisão.
8. Carga em recarga completa: adequada ao tamanho do desafio; para grandes volumes seria preciso upsert/incremental.

## 6. O que foi e o que não foi verificado

- **Verificado**: 74 testes automatizados (normalização, cliente de CEP com respostas simuladas —
  sucesso, fallback, timeout, cache positivo/negativo, JSON inválido —, regras de resolução e pipeline
  ponta a ponta com o CSV real); execução completa em modo `--sem-api` com SQLite.
- **Não verificado**: chamadas reais a ViaCEP/BrasilAPI (o ambiente de desenvolvimento não tinha esses
  domínios liberados) e carga em PostgreSQL real (o código usa SQLAlchemy e tipos portáveis, testado
  em SQLite). Rodar `python main.py` no ambiente do desafio é o primeiro passo de validação, e o
  resumo impresso (`divergencias_cep_bairro`, `revisao_manual`, `cache_cep`) mostra imediatamente
  como as APIs se comportaram.
