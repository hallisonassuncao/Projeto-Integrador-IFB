"""Roteamento das rotas da API REST do app clientes."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditoriaViewSet,
    ClienteViewSet,
    VendedorViewSet,
    disparar_etl,
    relatorio_bairros,
    relatorio_resumo,
)

router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")
router.register(r"auditoria", AuditoriaViewSet, basename="auditoria")
router.register(r"vendedores", VendedorViewSet, basename="vendedor")

urlpatterns = [
    path("", include(router.urls)),
    path("relatorios/bairros/", relatorio_bairros, name="relatorio-bairros"),
    path("relatorios/resumo/", relatorio_resumo, name="relatorio-resumo"),
    path("etl/executar/", disparar_etl, name="disparar-etl"),
]
