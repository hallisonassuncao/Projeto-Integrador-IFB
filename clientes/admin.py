"""Configuração da interface visual administrativa (Django Admin)."""
from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import AuditoriaTratamento, ClienteTratado, Vendedor


class AuditoriaInline(admin.TabularInline):
    model = AuditoriaTratamento
    extra = 0
    can_delete = False
    readonly_fields = [
        "campo",
        "valor_original",
        "valor_tratado",
        "criterio",
        "fonte",
        "revisao_manual",
        "executado_em",
    ]


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ["id_vendedor", "nome_vendedor", "total_clientes"]
    search_fields = ["nome_vendedor"]

    def total_clientes(self, obj):
        return obj.clientes.count()

    total_clientes.short_description = "Total de Clientes"


@admin.register(ClienteTratado)
class ClienteTratadoAdmin(admin.ModelAdmin):
    list_display = [
        "id_cliente",
        "razao_social",
        "cnpj",
        "telefone",
        "bairro_badge",
        "subdivisao",
        "cep",
        "vendedor",
        "divergencia_badge",
        "revisao_badge",
    ]
    list_filter = [
        "bairro",
        "subdivisao",
        "divergencia_cep_bairro",
        "revisao_manual",
        "uf",
        "vendedor",
        "data_ambigua",
    ]
    search_fields = [
        "id_cliente",
        "razao_social",
        "cnpj",
        "bairro",
        "bairro_informado",
        "cep",
        "email",
    ]
    inlines = [AuditoriaInline]

    fieldsets = (
        ("Identificação", {"fields": ("id_cliente", "razao_social", "vendedor")}),
        ("Fiscal e Contato", {"fields": ("cnpj", "cnpj_dv_valido", "telefone", "telefone_tipo", "email", "email_valido")}),
        ("Localização e Georreferenciamento", {
            "fields": (
                "cep", "cep_status", "bairro_informado", "bairro", "subdivisao",
                "bairro_fonte", "cidade", "uf", "divergencia_cep_bairro"
            )
        }),
        ("Governança e Auditoria", {"fields": ("data_cadastro", "data_ambigua", "revisao_manual")}),
    )

    def bairro_badge(self, obj):
        if not obj.bairro:
            return mark_safe('<span style="color: red; font-weight: bold;">(Sem Bairro)</span>')
        return obj.bairro

    bairro_badge.short_description = "Bairro"

    def divergencia_badge(self, obj):
        if obj.divergencia_cep_bairro:
            return mark_safe('<span style="color: #e67e22; font-weight: bold;">⚠ Divergência</span>')
        return "✔ OK"

    divergencia_badge.short_description = "Div. CEP"

    def revisao_badge(self, obj):
        if obj.revisao_manual:
            return mark_safe('<span style="background-color: #ffcccc; color: #cc0000; padding: 2px 6px; border-radius: 4px; font-weight: bold;">Revisar</span>')
        return "Conforme"

    revisao_badge.short_description = "Revisão Manual"


@admin.register(AuditoriaTratamento)
class AuditoriaTratamentoAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "cliente",
        "campo",
        "valor_original",
        "valor_tratado",
        "criterio",
        "fonte",
        "revisao_manual",
        "executado_em",
    ]
    list_filter = ["campo", "fonte", "revisao_manual", "executado_em"]
    search_fields = ["cliente__id_cliente", "cliente__razao_social", "campo", "criterio"]
    readonly_fields = [
        "cliente",
        "campo",
        "valor_original",
        "valor_tratado",
        "criterio",
        "fonte",
        "revisao_manual",
        "executado_em",
    ]
