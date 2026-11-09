"""Views e ViewSets do Django REST Framework para a Distribuidora Vetor."""
from django.core.management import call_command
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import AuditoriaTratamento, ClienteTratado, Vendedor
from .serializers import (
    AuditoriaTratamentoSerializer,
    ClienteTratadoComAuditoriaSerializer,
    ClienteTratadoSerializer,
    VendedorSerializer,
)


class VendedorViewSet(viewsets.ReadOnlyModelViewSet):
    """Listagem e detalhes dos Vendedores."""
    queryset = Vendedor.objects.all()
    serializer_class = VendedorSerializer


class ClienteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Listagem e detalhes dos Clientes Tratados.
    
    Permite filtrar por:
    - `bairro`: nome do bairro (ex.: ?bairro=Aguas Claras)
    - `uf`: sigla da UF (ex.: ?uf=DF)
    - `divergencia`: true/false (divergência entre CEP e bairro informado)
    - `revisao_manual`: true/false (clientes marcados para revisão humana)
    - `vendedor`: nome ou ID do vendedor
    """
    queryset = ClienteTratado.objects.select_related("vendedor").all()

    def get_serializer_class(self):
        com_auditoria = self.request.query_params.get("com_auditoria", "").lower() in ("true", "1")
        if self.action == "retrieve" and com_auditoria:
            return ClienteTratadoComAuditoriaSerializer
        return ClienteTratadoSerializer

    @action(detail=True, methods=["get"])
    def auditoria(self, request, pk=None):
        """Retorna exclusivamente a trilha de auditoria deste cliente."""
        cliente = self.get_object()
        auditorias = cliente.auditorias.all()
        serializer = AuditoriaTratamentoSerializer(auditorias, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        bairro = params.get("bairro")
        if bairro:
            qs = qs.filter(bairro__icontains=bairro)

        uf = params.get("uf")
        if uf:
            qs = qs.filter(uf__iexact=uf)

        divergencia = params.get("divergencia")
        if divergencia is not None:
            if divergencia.lower() in ("true", "1"):
                qs = qs.filter(divergencia_cep_bairro=True)
            elif divergencia.lower() in ("false", "0"):
                qs = qs.filter(divergencia_cep_bairro=False)

        revisao = params.get("revisao_manual")
        if revisao is not None:
            if revisao.lower() in ("true", "1"):
                qs = qs.filter(revisao_manual=True)
            elif revisao.lower() in ("false", "0"):
                qs = qs.filter(revisao_manual=False)

        vendedor = params.get("vendedor")
        if vendedor:
            if vendedor.isdigit():
                qs = qs.filter(vendedor_id=int(vendedor))
            else:
                qs = qs.filter(vendedor__nome_vendedor__icontains=vendedor)

        return qs


class AuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consulta da trilha de auditoria do ETL.
    
    Filtros suportados:
    - `cliente`: ID do cliente (ex.: ?cliente=CLI0001)
    - `campo`: campo tratado (ex.: ?campo=bairro)
    - `revisao_manual`: true/false
    - `fonte`: regra, api_cep, etc.
    """
    queryset = AuditoriaTratamento.objects.select_related("cliente").all()
    serializer_class = AuditoriaTratamentoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        cliente = params.get("cliente")
        if cliente:
            qs = qs.filter(cliente_id=cliente)

        campo = params.get("campo")
        if campo:
            qs = qs.filter(campo__iexact=campo)

        revisao = params.get("revisao_manual")
        if revisao is not None:
            if revisao.lower() in ("true", "1"):
                qs = qs.filter(revisao_manual=True)
            elif revisao.lower() in ("false", "0"):
                qs = qs.filter(revisao_manual=False)

        fonte = params.get("fonte")
        if fonte:
            qs = qs.filter(fonte__iexact=fonte)

        return qs


@api_view(["GET"])
def relatorio_bairros(request):
    """Retorna a contagem de clientes agrupados por Bairro Canônico e Subdivisão."""
    dados = (
        ClienteTratado.objects.values("bairro", "subdivisao")
        .annotate(quantidade=Count("id_cliente"))
        .order_by("-quantidade", "bairro")
    )
    return Response(list(dados))


@api_view(["GET"])
def relatorio_resumo(request):
    """Retorna o resumo estatístico consolidado da qualidade da base tratada."""
    total_clientes = ClienteTratado.objects.count()
    total_auditoria = AuditoriaTratamento.objects.count()
    divergencias = ClienteTratado.objects.filter(divergencia_cep_bairro=True).count()
    revisoes = ClienteTratado.objects.filter(revisao_manual=True).count()
    datas_ambiguas = ClienteTratado.objects.filter(data_ambigua=True).count()
    ceps_ok = ClienteTratado.objects.filter(cep_status="ok").count()
    ceps_invalidos = ClienteTratado.objects.filter(cep_status="invalido").count()
    ceps_ausentes = ClienteTratado.objects.filter(cep_status="ausente").count()

    return Response({
        "total_clientes": total_clientes,
        "total_registros_auditoria": total_auditoria,
        "clientes_com_divergencia_cep_bairro": divergencias,
        "clientes_marcados_revisao_manual": revisoes,
        "datas_ambiguas": datas_ambiguas,
        "cep_status": {
            "ok": ceps_ok,
            "invalido": ceps_invalidos,
            "ausente": ceps_ausentes,
        },
    })


@api_view(["POST"])
def disparar_etl(request):
    """Executa o pipeline de ETL diretamente via chamada de API."""
    sem_api = request.data.get("sem_api", False) if isinstance(request.data, dict) else False
    try:
        call_command("rodar_etl", sem_api=bool(sem_api))
        return Response(
            {"mensagem": "ETL executado com sucesso e banco de dados atualizado!"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"erro": f"Falha na execução do ETL: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
