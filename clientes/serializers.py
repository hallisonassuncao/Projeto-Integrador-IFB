"""Serializadores do Django REST Framework para os dados tratados e auditoria."""
from rest_framework import serializers
from .models import AuditoriaTratamento, ClienteTratado, Vendedor


class VendedorSerializer(serializers.ModelSerializer):
    total_clientes = serializers.IntegerField(source="clientes.count", read_only=True)

    class Meta:
        model = Vendedor
        fields = ["id_vendedor", "nome_vendedor", "total_clientes"]


class AuditoriaTratamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditoriaTratamento
        fields = [
            "id",
            "cliente_id",
            "campo",
            "valor_original",
            "valor_tratado",
            "criterio",
            "fonte",
            "revisao_manual",
            "executado_em",
        ]


class ClienteTratadoSerializer(serializers.ModelSerializer):
    vendedor_nome = serializers.CharField(source="vendedor.nome_vendedor", read_only=True)
    total_auditorias = serializers.IntegerField(source="auditorias.count", read_only=True)

    class Meta:
        model = ClienteTratado
        fields = [
            "id_cliente",
            "razao_social",
            "cnpj",
            "cnpj_dv_valido",
            "telefone",
            "telefone_tipo",
            "email",
            "email_valido",
            "cep",
            "cep_status",
            "bairro_informado",
            "bairro",
            "subdivisao",
            "bairro_fonte",
            "divergencia_cep_bairro",
            "revisao_manual",
            "cidade",
            "uf",
            "data_cadastro",
            "data_ambigua",
            "vendedor",
            "vendedor_nome",
            "total_auditorias",
        ]


class ClienteTratadoComAuditoriaSerializer(ClienteTratadoSerializer):
    auditorias = AuditoriaTratamentoSerializer(many=True, read_only=True)

    class Meta(ClienteTratadoSerializer.Meta):
        fields = ClienteTratadoSerializer.Meta.fields + ["auditorias"]

