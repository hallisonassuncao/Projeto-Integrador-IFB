"""Roteamento principal de URLs do projeto Distribuidora Vetor."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("clientes.urls")),
    path("", include("clientes.urls")),
]
