"""Modelos relacionais do Django para o Desafio Distribuidora Vetor."""
from django.db import models


class Vendedor(models.Model):
    id_vendedor = models.AutoField(primary_key=True)
    nome_vendedor = models.CharField("Nome do Vendedor", max_length=100, unique=True)

    class Meta:
        db_table = "vendedores"
        verbose_name = "Vendedor"
        verbose_name_plural = "Vendedores"
        ordering = ["nome_vendedor"]

    def __str__(self):
        return self.nome_vendedor


class ClienteTratado(models.Model):
    id_cliente = models.CharField("ID do Cliente", max_length=20, primary_key=True)
    razao_social = models.CharField("Razão Social", max_length=200, null=True, blank=True)
    cnpj = models.CharField("CNPJ", max_length=18, null=True, blank=True)
    cnpj_dv_valido = models.BooleanField("CNPJ DV Válido", null=True, blank=True)
    telefone = models.CharField("Telefone (E.164)", max_length=15, null=True, blank=True)
    telefone_tipo = models.CharField("Tipo do Telefone", max_length=10, null=True, blank=True)
    email = models.CharField("E-mail", max_length=150, null=True, blank=True)
    email_valido = models.BooleanField("E-mail Válido", null=True, blank=True)
    cep = models.CharField("CEP", max_length=9, null=True, blank=True)
    cep_status = models.CharField("Status do CEP", max_length=30, null=True, blank=True)
    bairro_informado = models.CharField("Bairro Informado", max_length=100, null=True, blank=True)
    bairro = models.CharField("Bairro Canônico", max_length=100, null=True, blank=True)
    subdivisao = models.CharField("Subdivisão", max_length=30, null=True, blank=True)
    bairro_fonte = models.CharField("Fonte do Bairro", max_length=30, null=True, blank=True)
    divergencia_cep_bairro = models.BooleanField("Divergência CEP x Bairro", default=False)
    revisao_manual = models.BooleanField("Exige Revisão Manual", default=False)
    cidade = models.CharField("Cidade", max_length=80, null=True, blank=True)
    uf = models.CharField("UF", max_length=2, null=True, blank=True)
    data_cadastro = models.DateField("Data de Cadastro", null=True, blank=True)
    data_ambigua = models.BooleanField("Data Ambígua", default=False)
    vendedor = models.ForeignKey(
        Vendedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes",
        verbose_name="Vendedor Responsável",
    )

    class Meta:
        db_table = "clientes_tratados"
        verbose_name = "Cliente Tratado"
        verbose_name_plural = "Clientes Tratados"
        ordering = ["id_cliente"]

    def __str__(self):
        return f"{self.id_cliente} - {self.razao_social or 'Sem Razão Social'}"


class AuditoriaTratamento(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(
        ClienteTratado,
        on_delete=models.CASCADE,
        related_name="auditorias",
        db_column="id_cliente",
        verbose_name="Cliente",
    )
    campo = models.CharField("Campo Alterado", max_length=30, null=True, blank=True)
    valor_original = models.TextField("Valor Original", null=True, blank=True)
    valor_tratado = models.TextField("Valor Tratado", null=True, blank=True)
    criterio = models.TextField("Critério Aplicado", null=True, blank=True)
    fonte = models.CharField("Fonte", max_length=30, null=True, blank=True)
    revisao_manual = models.BooleanField("Exige Revisão Manual", default=False)
    executado_em = models.DateTimeField("Executado em", auto_now_add=True)

    class Meta:
        db_table = "auditoria_tratamento"
        verbose_name = "Registro de Auditoria"
        verbose_name_plural = "Trilha de Auditoria"
        ordering = ["id"]

    def __str__(self):
        return f"Auditoria #{self.id} [{self.cliente_id}] - {self.campo}"
