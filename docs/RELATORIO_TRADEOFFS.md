# Relatório de trade-offs — ETL Distribuidora Vetor

## Problema

A base contém 47 clientes, com 25 grafias diferentes de bairro e 1 registro sem bairro, totalizando 26 valores distintos antes do tratamento. Também apresenta formatos inconsistentes de telefone, data e CNPJ, além de CEPs ausentes, inválidos ou divergentes. Sem normalização, os relatórios regionais ficam fragmentados, dificultando a análise dos quatro bairros representados na amostra.

## O que foi automatizado — e por quê

| Decisão | Justificativa |
|---|---|
| Normalização textual (caixa, acentos, espaços, `DF` e parênteses) | Padroniza grafias de maneira determinística, reproduzível e testável. |
| Dicionário de bairros em CSV | Permite mapear variantes para nomes canônicos, mantendo regras explícitas e auditáveis. |
| Padronização de CNPJ, telefone, datas e e-mails | Uniformiza os dados e sinaliza valores inválidos sem descartar registros. |
| Consulta ViaCEP com fallback BrasilAPI e cache SQLite | Enriquece os dados, reduz requisições repetidas e permite reexecuções mais rápidas. |
| Resolução de divergências CEP × bairro | A API prevalece quando ambos são mapeados e divergem; a decisão é registrada na auditoria. |
| Auditoria e carga idempotente | Preserva o histórico das decisões de tratamento e evita duplicação de clientes nas reexecuções. |

## O que ficou para tratamento manual — e por quê

| Situação | Justificativa |
|---|---|
| Bairro ausente ou não resolvido | Não é possível atribuir uma localidade confiável sem informação suficiente. |
| Bairros desconhecidos e correspondências *fuzzy* | A similaridade textual pode associar localidades diferentes. |
| Bairro da API fora do dicionário | Pode representar uma nova variante legítima ou inconsistência da fonte externa. |
| CEP pertencente a outra UF | Indica possível erro cadastral que exige confirmação. |
| Datas ambíguas | Adota-se `dd/mm`, com sinalização, pois não há segunda fonte para confirmar a interpretação. |
| CNPJ com dígitos verificadores inválidos | A base é sintética; rejeitar esses valores eliminaria os 47 registros. |

## Trade-offs principais

1. **Precisão × cobertura.** A prioridade é evitar a atribuição de bairros sem evidência suficiente. Registros não resolvidos permanecem nulos e são sinalizados para revisão manual.

2. **Dependência externa × autonomia.** ViaCEP e BrasilAPI oferecem referência geográfica, mas podem falhar ou devolver nomes não padronizados. O cache local, o fallback e a execução offline (`--sem-api`) reduzem essa dependência.

3. **Bairro-pai × subdivisão.** Os relatórios agrupam clientes pelo bairro canônico, enquanto subdivisões como Sul, Norte e Areal são preservadas separadamente.

4. **Rigor × utilidade dos dados.** Os 47 CNPJs possuem dígitos verificadores inválidos. Optou-se por preservar os registros e sinalizar a inconsistência, em vez de descartar toda a base fictícia.

5. **Carga individual × desempenho.** O uso de `update_or_create` torna a carga idempotente e preserva clientes criados pela API. Para grandes volumes, seria necessário avaliar operações em lote.

6. **Normalização do banco × simplicidade.** Vendedores possuem tabela própria, enquanto bairro e CEP permanecem associados ao cliente, facilitando consultas e relatórios.

## Resultados verificados

| Indicador | Resultado |
|---|---|
| Clientes processados | 47 |
| Vendedores | 5 |
| Grafias de bairros antes do tratamento | 25 + 1 registro vazio |
| Bairros canônicos | 4 |
| Clientes com CEP válido | 31 |
| CEPs distintos consultados na execução real anterior | 14 |
| Requisições externas nessa execução | 16, sem falhas |
| CEPs não encontrados | 2 distintos, afetando 3 clientes |
| Bairro informado e API concordam | 27 |
| Bairro obtido somente pela API | 1 |
| Bairro obtido somente do cadastro | 18 |
| Divergência CEP × bairro | 1 (CLI0002) |
| Cliente sem bairro resolvido | 1 (CLI0047) |
| Clientes em revisão manual após correção | **1 (CLI0047)** |
| Registros de auditoria | 194 |
| Testes automatizados | **121 aprovados** |

Na primeira execução com consultas externas, oito clientes foram sinalizados porque a API retornou nomes ausentes do dicionário: "Setor Habitacional Vicente Pires" (5) e "Areal" (3). Essas variantes foram incorporadas ao dicionário, eliminando a necessidade de revisão desses oito registros. A associação de Areal a Águas Claras é uma premissa baseada na amostra, sem confirmação oficial no pipeline.

O cliente CLI0002 apresentou divergência: o cadastro informava "Sul (Águas Claras)", enquanto o ViaCEP retornou "Taguatinga Norte". Conforme a regra definida, prevaleceu a API, com divergência registrada para conferência posterior.

Após corrigir a função `resolver_bairro`, o cliente CLI0047, sem bairro resolvido, passou a ser sinalizado para revisão manual. A nova execução manteve os 47 clientes, 5 vendedores, 4 bairros e 194 registros de auditoria, com 1 cliente em revisão.

Os 121 testes automatizados passaram em 35,58 segundos. O comando `python manage.py check` também não identificou problemas. Na execução mais recente, as consultas de CEP foram atendidas pelo cache local.

## Próximos passos

Revisar manualmente o CLI0047, conferir a divergência do CLI0002, corrigir os CEPs inexistentes (72110-800 e 71900-000), definir uma política de validação de CNPJ para produção e avaliar carga incremental para bases maiores.
