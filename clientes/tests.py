"""Testes automatizados do Django para modelos, comando de ETL e API REST."""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AuditoriaTratamento, ClienteTratado, Vendedor


class ModelosTestCase(TestCase):
    def setUp(self):
        self.vendedor = Vendedor.objects.create(nome_vendedor="Vendedor Teste")
        self.cliente = ClienteTratado.objects.create(
            id_cliente="CLI9999",
            razao_social="Empresa Teste LTDA",
            cnpj="12.345.678/0001-90",
            bairro="Águas Claras",
            subdivisao="Sul",
            cep="71926-750",
            vendedor=self.vendedor,
        )
        self.auditoria = AuditoriaTratamento.objects.create(
            cliente=self.cliente,
            campo="bairro",
            valor_original="aguas claras sul",
            valor_tratado="Águas Claras / Sul",
            criterio="dicionario",
            fonte="regra",
        )

    def test_criacao_modelos(self):
        self.assertEqual(Vendedor.objects.count(), 1)
        self.assertEqual(ClienteTratado.objects.count(), 1)
        self.assertEqual(AuditoriaTratamento.objects.count(), 1)
        self.assertEqual(self.cliente.vendedor.nome_vendedor, "Vendedor Teste")
        self.assertEqual(self.cliente.auditorias.first().campo, "bairro")


class ApiRestTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        v1 = Vendedor.objects.create(nome_vendedor="Carlos Vendedor")
        c1 = ClienteTratado.objects.create(
            id_cliente="CLI0001",
            razao_social="Supermercado Alvorada",
            bairro="Águas Claras",
            subdivisao="Norte",
            uf="DF",
            divergencia_cep_bairro=False,
            revisao_manual=False,
            vendedor=v1,
        )
        c2 = ClienteTratado.objects.create(
            id_cliente="CLI0002",
            razao_social="Drogaria Central",
            bairro="Taguatinga",
            subdivisao="Sul",
            uf="DF",
            divergencia_cep_bairro=True,
            revisao_manual=True,
            vendedor=v1,
        )
        AuditoriaTratamento.objects.create(
            cliente=c1,
            campo="bairro",
            valor_original="norte aguas claras",
            valor_tratado="Águas Claras / Norte",
            criterio="dicionario",
            fonte="regra",
        )

    def test_listar_clientes(self):
        url = reverse("cliente-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        dados = res.data.get("results", res.data)
        self.assertGreaterEqual(len(dados), 2)

    def test_filtrar_clientes_por_bairro(self):
        url = reverse("cliente-list") + "?bairro=Taguatinga"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        dados = res.data.get("results", res.data)
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["id_cliente"], "CLI0002")

    def test_detalhes_cliente(self):
        url = reverse("cliente-detail", args=["CLI0001"])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id_cliente"], "CLI0001")
        self.assertEqual(res.data["total_auditorias"], 1)
        self.assertNotIn("auditorias", res.data)

    def test_detalhes_cliente_com_auditoria_query_param(self):
        url = reverse("cliente-detail", args=["CLI0001"]) + "?com_auditoria=true"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id_cliente"], "CLI0001")
        self.assertIn("auditorias", res.data)
        self.assertEqual(len(res.data["auditorias"]), 1)

    def test_endpoint_exclusivo_auditoria_do_cliente(self):
        url = reverse("cliente-auditoria", args=["CLI0001"])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["campo"], "bairro")

    def test_relatorio_bairros(self):
        url = reverse("relatorio-bairros")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(res.data, list))
        self.assertGreaterEqual(len(res.data), 1)
        self.assertIn("quantidade", res.data[0])

    def test_relatorio_resumo(self):
        url = reverse("relatorio-resumo")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("total_clientes", res.data)
        self.assertIn("clientes_com_divergencia_cep_bairro", res.data)


class AdminPanelTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser("admin_test", "adm@test.com", "senha123")
        self.client.login(username="admin_test", password="senha123")
        v = Vendedor.objects.create(nome_vendedor="Vendedor Admin Teste")
        c = ClienteTratado.objects.create(
            id_cliente="CLI0001",
            razao_social="Empresa Admin Teste",
            bairro="Taguatinga",
            subdivisao="Norte",
            cep="72140-010",
            divergencia_cep_bairro=True,
            revisao_manual=True,
            vendedor=v,
        )
        AuditoriaTratamento.objects.create(
            cliente=c,
            campo="bairro",
            valor_original="taguatinga norte",
            valor_tratado="Taguatinga / Norte",
            criterio="dicionario",
            fonte="regra",
        )

    def test_admin_clientes_listagem(self):
        res = self.client.get("/admin/clientes/clientetratado/")
        self.assertEqual(res.status_code, 200)

    def test_admin_clientes_edicao_com_inline(self):
        res = self.client.get("/admin/clientes/clientetratado/CLI0001/change/")
        self.assertEqual(res.status_code, 200)

    def test_admin_auditoria_listagem(self):
        res = self.client.get("/admin/clientes/auditoriatratamento/")
        self.assertEqual(res.status_code, 200)

    def test_admin_vendedores_listagem(self):
        res = self.client.get("/admin/clientes/vendedor/")
        self.assertEqual(res.status_code, 200)

