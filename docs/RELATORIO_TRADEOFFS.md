# Relatório de trade-offs — ETL Distribuidora Vetor

## Problema

47 clientes com 25 grafias diferentes de bairro (mais 1 registro sem bairro), 4 formatos de telefone, 4 formatos de data, CNPJ com e sem máscara e aproximadamente 34% dos CEPs ausentes ou inválidos. Sem tratamento, um relatório por bairro mostra 25 grafias diferentes onde existem 4 bairros.

## O que foi automatizado — e por quê

| Decisão | Motivo |
|---|---|
| Normalização textual determinística (caixa, acento, `DF`, parênteses) | Resolve a maior parte das variantes sem custo externo; é reprodutível e testável |
| Dicionário variante → bairro canônico em arquivo CSV | Regra explícita e auditável; quem conhece o negócio amplia sem editar código |
| Padronização de CNPJ, telefone (E.164) e datas | Uniformiza os dados e registra alterações e inconsistências na auditoria |
| Consulta de CEP (ViaCEP → BrasilAPI) com cache | Fornece referência geográfica externa; o cache evita repetir chamadas e torna reexecuções rápidas e estáveis |
| Divergência CEP × bairro: a API prevalece, com flag | A fonte estruturada prevalece sobre o texto livre, mas a decisão fica registrada para conferência |

## O que ficou para tratamento manual — e por quê

| Item | Motivo |
|---|---|
| Bairro ausente ou sem resolução | Não é possível determinar uma localidade confiável sem informações suficientes |
| Bairros fora do dicionário e correspondências *fuzzy* | Aproximar texto automaticamente pode juntar bairros diferentes; um erro silencioso contamina o relatório |
| Bairro da API que não existe no dicionário | Pode ser variante nova legítima ou erro da API; exige avaliação |
| CEPs de outra UF | Indício de erro cadastral, não apenas de grafia |
| Datas ambíguas (`dd/mm` × `mm/dd`) | Sem segunda fonte não há como confirmar; fica a premissa `dd/mm` + flag `data_ambigua` |
| CNPJ com dígito verificador inválido | Descartar apagaria a base inteira; o valor é mantido e sinalizado |

## Trade-offs principais

1. **Precisão × cobertura.** Preferimos deixar um bairro nulo com revisão manual a atribuir uma localidade sem evidência. O custo é trabalho manual residual; o ganho é evitar classificações incorretas nos relatórios.

2. **Dependência externa × autonomia.** A API melhora a qualidade, mas pode falhar ou devolver nomes fora do padrão. Mitigação: fallback entre dois provedores, cache local, falhas de rede nunca cacheadas e execução offline (`--sem-api`) usando o dicionário.

3. **Bairro-pai × subdivisão.** Agrupar em "Águas Claras" perde o recorte Sul/Norte; guardá-lo em coluna própria permite as duas visões, ao custo de uma coluna adicional.

4. **Rigor × utilidade (CNPJ).** Validar e rejeitar seria uma alternativa em produção, mas aqui geraria uma tabela vazia. Optamos por manter, sinalizar e documentar o limite.

5. **Carga linha a linha × em lote.** A carga é idempotente (`update_or_create` por `id_cliente`) e preserva clientes criados pela API, mas grava registro a registro: adequado ao volume do desafio, não a milhões de linhas.

6. **Banco normalizado × tabela larga.** Vendedor ganhou tabela própria porque a API o exige como entidade com CRUD. Bairro e CEP continuam colunas do cliente: simplifica os relatórios agrupados por bairro, ao custo de repetir informações.

## Resultado (execução real: ViaCEP + PostgreSQL)

| Indicador | Valor |
|---|---|
| Grafias de bairro → bairros canônicos | 25 (+1 vazio) → **4** (Águas Claras, Taguatinga, Vicente Pires, Guará) |
| CEPs distintos consultados na execução real anterior (31 clientes com CEP válido) | 14 (16 requisições, 0 falhas); 2 não encontrados nas APIs |
| Bairro informado e CEP concordam | 27 |
| Bairro obtido somente pela API | 1 |
| Divergência CEP × bairro (API prevalece) | 1 (CLI0002) |
| Só o bairro informado, sem confirmação pela API | 18 (15 sem CEP utilizável; 3 com CEP bem formatado, mas inexistente nas APIs) |
| Sem bairro resolvido | 1 (CLI0047, sem bairro nem CEP) |
| Fila de revisão manual após a correção | **1 (CLI0047)** |
| Linhas de auditoria | **194** |
| Testes automatizados | **121 aprovados** |

- Na **primeira rodada**, 8 clientes foram sinalizados para revisão manual porque a API devolveu nomes fora do dicionário: "Setor Habitacional Vicente Pires" (5) e "Areal" (3). Em todos esses casos, o bairro informado já apontava para a mesma localidade. Os dois nomes foram incorporados ao dicionário (`Vicente Pires` e `Águas Claras / Areal`), resolvendo esses 8 casos. Após a correção da função `resolver_bairro`, o cliente CLI0047, sem bairro informado e sem CEP, passou a ser sinalizado para revisão manual. Assim, a fila atual contém **1 cliente**.

- "Areal → Águas Claras" é uma **premissa assumida** a partir da base (os 3 clientes com esse retorno informaram Águas Claras), sem fonte oficial no pipeline.

- CLI0002: informado "Sul (Águas Claras)", ViaCEP devolveu "Taguatinga Norte". A API prevaleceu e o caso está registrado na auditoria para conferência; é o único ponto em que o pipeline contrariou o cadastro.

- Foram identificadas 6 datas ambíguas (interpretadas como `dd/mm`), 10 e-mails inválidos e 47 CNPJs com dígitos verificadores inválidos (base sintética), mantidos e sinalizados.

- A execução mais recente do ETL processou **47 clientes, 5 vendedores e 4 bairros**, gerando 194 linhas de auditoria e identificando 1 cliente para revisão manual. As consultas de CEP foram atendidas pelo cache local, sem novas requisições externas.

## Validação dos testes

O projeto foi validado com os seguintes comandos:

`python -m pytest -q`

**Resultado:** 121 testes aprovados em 35,58 segundos, sem falhas.

`python manage.py check`

**Resultado:** `System check identified no issues (0 silenced)`.

Os testes abrangem normalização, regras de resolução, consulta de CEP com respostas simuladas, cache, persistência, idempotência e funcionalidades da API REST.

## Próximos passos

Revisar manualmente o cliente CLI0047, que não possui bairro resolvido nem CEP; corrigir os CEPs dos 3 clientes cujos códigos não foram encontrados nas APIs (72110-800 e 71900-000); conferir a divergência entre CEP e bairro do cliente CLI0002; definir uma política para CNPJs com dígitos verificadores inválidos (quarentena ou rejeição) e, em produção, avaliar a implementação de carga incremental.