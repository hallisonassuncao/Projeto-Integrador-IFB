"""Comando do Django para executar o pipeline de ETL e popular o banco de dados."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction

from etl.cep_client import ClienteCep
from etl.normalizers import carregar_dicionario
from etl.pipeline import extrair, resumir, transformar
from clientes.models import AuditoriaTratamento, ClienteTratado, Vendedor


class Command(BaseCommand):
    help = "Executa o pipeline de ETL da Distribuidora Vetor e popula os modelos do Django."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default="data/clientes_distribuidora_vetor.csv",
            help="Caminho do arquivo CSV de clientes.",
        )
        parser.add_argument(
            "--cache",
            default="cache/cep_cache.sqlite",
            help="Caminho do cache SQLite para consultas de CEP.",
        )
        parser.add_argument(
            "--sem-api",
            action="store_true",
            help="Executa o pipeline offline sem consultar APIs de CEP.",
        )
        parser.add_argument(
            "--dicionario",
            default=None,
            help="Caminho do dicionário de bairros CSV personalizado.",
        )

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        caminho_csv = Path(options["csv"])
        if not caminho_csv.is_absolute():
            caminho_csv = base_dir / caminho_csv

        caminho_cache = Path(options["cache"])
        if not caminho_cache.is_absolute():
            caminho_cache = base_dir / caminho_cache

        caminho_dic = options["dicionario"]
        if caminho_dic and not Path(caminho_dic).is_absolute():
            caminho_dic = base_dir / caminho_dic

        self.stdout.write(self.style.NOTICE("===> Iniciando Pipeline de ETL com Django..."))

        sem_api = options["sem_api"]
        cliente_cep = None if sem_api else ClienteCep(caminho_cache)
        try:
            linhas = extrair(caminho_csv)
            dicionario = carregar_dicionario(caminho_dic)
            clientes_dados, auditoria_dados = transformar(linhas, dicionario, cliente_cep)

            self.stdout.write(
                f"Foram transformados {len(clientes_dados)} clientes e {len(auditoria_dados)} linhas de auditoria."
            )

            # Persistência atômica no banco do Django
            with transaction.atomic():
                self.stdout.write("Limpando registros anteriores...")
                AuditoriaTratamento.objects.all().delete()
                ClienteTratado.objects.all().delete()

                # 1. Identificar e salvar os Vendedores
                vendedores_unicos = {
                    c.get("vendedor_responsavel")
                    for c in clientes_dados
                    if c.get("vendedor_responsavel")
                }
                mapa_vendedores = {}
                for nome in sorted(vendedores_unicos):
                    vend, _ = Vendedor.objects.get_or_create(nome_vendedor=nome)
                    mapa_vendedores[nome] = vend

                # 2. Salvar Clientes Tratados
                instancias_clientes = []
                for c in clientes_dados:
                    nome_vendedor = c.get("vendedor_responsavel")
                    vend_obj = mapa_vendedores.get(nome_vendedor)
                    instancias_clientes.append(
                        ClienteTratado(
                            id_cliente=c["id_cliente"],
                            razao_social=c["razao_social"],
                            cnpj=c["cnpj"],
                            cnpj_dv_valido=c["cnpj_dv_valido"],
                            telefone=c["telefone"],
                            telefone_tipo=c["telefone_tipo"],
                            email=c["email"],
                            email_valido=c["email_valido"],
                            cep=c["cep"],
                            cep_status=c["cep_status"],
                            bairro_informado=c["bairro_informado"],
                            bairro=c["bairro"],
                            subdivisao=c["subdivisao"],
                            bairro_fonte=c["bairro_fonte"],
                            divergencia_cep_bairro=c["divergencia_cep_bairro"],
                            revisao_manual=c["revisao_manual"],
                            cidade=c["cidade"],
                            uf=c["uf"],
                            data_cadastro=c["data_cadastro"],
                            data_ambigua=c["data_ambigua"],
                            vendedor=vend_obj,
                        )
                    )
                ClienteTratado.objects.bulk_create(instancias_clientes)

                # 3. Salvar Auditoria
                instancias_auditoria = [
                    AuditoriaTratamento(
                        cliente_id=a["id_cliente"],
                        campo=a["campo"],
                        valor_original=a["valor_original"],
                        valor_tratado=a["valor_tratado"],
                        criterio=a["criterio"],
                        fonte=a["fonte"],
                        revisao_manual=a["revisao_manual"],
                    )
                    for a in auditoria_dados
                ]
                AuditoriaTratamento.objects.bulk_create(instancias_auditoria)

            resumo = resumir(linhas, clientes_dados, auditoria_dados, cliente_cep)
            self.stdout.write(self.style.SUCCESS("✔ Pipeline de ETL executado e persistido com sucesso!"))
            self.stdout.write(json.dumps(resumo, ensure_ascii=False, indent=2, default=str))

        finally:
            if cliente_cep:
                cliente_cep.fechar()
