# ETL — Distribuidora Vetor (Desafio Técnico 1) Desafio PRIMORA

Pipeline em Python que limpa e enriquece a base de clientes (bairro, CEP, CNPJ, telefone, data, e-mail),
grava em banco SQL e registra uma trilha de auditoria (valor original → valor tratado → critério/fonte).

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/vetor
python main.py            # ou: python main.py --sem-api --db-url sqlite:///vetor.db
pytest
```

- Documentação técnica: 
- Relatório de trade-offs: 
- Dicionário de bairros (editável):

- $env:DATABASE_URL="postgresql+psycopg2://postgres:607337@localhost:5432/vetor"

python main.py
   
1. Entrar na pasta e ativar o ambiente
 cd C:\Users\Halli\Downloads\etl_vetor\etl_vetor

 python -m venv .venv
 
.venv\Scripts\Activate.ps1

1. pip install -r requirements.txt

1. pytest

2. Rodar o ETL no PostgreSQL (entrega oficial) usar a senha do postgres

$env:DATABASE_URL="postgresql+psycopg2://postgres:SUA_SENHA@localhost:5432/vetor"
python main.py

3. Testar o pipeline sem PostgreSQL e sem internet

python main.py --sem-api --db-url sqlite:///vetor.db

3. Rodar o ETL em SQLite (sem servidor)

pip install sqlalchemy
pip install requests
python main.py --db-url sqlite:///vetor.db

3.1 Crie o banco vetor no PostgreSQL local:

psql -U postgres -c "CREATE DATABASE vetor;"

Defina a URL de conexão, ajustando usuário, senha e porta ao seu ambiente:

# Linux
export DATABASE_URL=postgresql+psycopg2://postgres:SUA_SENHA@localhost:5432/vetor
# Windows 
$env:DATABASE_URL="postgresql+psycopg2://postgres:SUA_SENHA@localhost:5432/vetor"

Execute:

python main.py

5. Rodar os testes

pytest

Devem passar 76 testes.

6. Conferir o resultado no PostgreSQL

& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d vetor -c "SELECT bairro, COUNT(*) FROM clientes_tratados GROUP BY bairro ORDER BY 2 DESC;"

& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d vetor -c "SELECT * FROM auditoria_tratamento WHERE revisao_manual;"


7. Conferir o resultado no SQLite

8. & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d vetor

9. Próximo teste: verificar as subdivisões
Ainda no PostgreSQL (vetor=#), execute:

SELECT
    bairro,
    subdivisao,
    COUNT(*) AS quantidade
FROM clientes_tratados
GROUP BY bairro, subdivisao
ORDER BY bairro, subdivisao;



python -c "import sqlite3; c=sqlite3.connect('vetor.db'); print(c.execute('SELECT bairro, COUNT(*) FROM clientes_tratados GROUP BY bairro').fetchall())"

## 10. Executando com o Framework Django

O projeto agora conta com integração completa ao **Django** e **Django REST Framework (DRF)**, fornecendo painel administrativo visual e API REST.

### 10.1 Aplicar as Migrações
```bash
python manage.py migrate
```

### 10.2 Executar o Pipeline de ETL pelo Django
```bash
python manage.py rodar_etl
# ou modo offline:
python manage.py rodar_etl --sem-api
```

### 10.3 Iniciar o Servidor Web
```bash
python manage.py runserver
```

Acesse no navegador:
* **Painel Administrativo do Django:** [http://localhost:8000/admin/](http://localhost:8000/admin/)
  * **Usuário:** `admin`
  * **Senha:** `admin123`
  * *Permite visualizar, filtrar por bairro/revisão, buscar clientes e ver todo o histórico de auditoria inline com badges visuais.*
* **Navegador da API REST (DRF):** [http://localhost:8000/api/](http://localhost:8000/api/)
  * `GET /api/clientes/` — Listagem de clientes com filtros por `bairro`, `uf`, `divergencia`, `revisao_manual` e `vendedor`.
  * `GET /api/clientes/{id}/` — Detalhes do cliente com lista de alterações de auditoria aninhadas.
  * `GET /api/auditoria/` — Trilha de auditoria das transformações.
  * `GET /api/vendedores/` — Vendedores e contagem de clientes atendidos.
  * `GET /api/relatorios/bairros/` — Agregação de clientes por bairro e subdivisão.
  * `GET /api/relatorios/resumo/` — Resumo estatístico de governança de dados.
  * `POST /api/etl/executar/` — Disparo do pipeline sob demanda via API.

### 10.4 Rodar os Testes
```bash
python manage.py test       # Testes dos modelos, comando e API REST do Django
pytest                      # 74 testes unitários de normalização e resiliência de CEP
```

