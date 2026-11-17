
"""Critério explícito para combinar o bairro informado com o bairro da API de CEP."""

from dataclasses import dataclass

from .normalizers import ResultadoBairro


@dataclass
class BairroResolvido:
    bairro: str | None
    subdivisao: str | None
    fonte: str  # api_cep | informado | api_cep+informado | nenhuma
    criterio: str
    divergencia: bool = False
    revisao_manual: bool = False


def resolver_bairro(
    informado: ResultadoBairro,
    api: ResultadoBairro | None
) -> BairroResolvido:
    """
    Combina o bairro informado pelo cliente com o bairro retornado
    pela API de CEP.

    Regras:
      1. Sem resposta utilizável da API:
         - Usa o bairro informado, se estiver mapeado.
         - Se nenhum bairro for resolvido, exige revisão manual.

      2. Informado ausente ou não mapeado e API mapeada:
         - Utiliza o bairro retornado pela API.

      3. Ambos mapeados e pertencentes ao mesmo bairro-pai:
         - Utiliza o bairro da API.
         - Preserva a subdivisão informada, se existir.

      4. Ambos mapeados, mas pertencentes a bairros diferentes:
         - A API prevalece.
         - Registra divergência entre CEP e bairro.

      5. Resultados fuzzy ou não mapeados:
         - São sinalizados para revisão manual conforme
           a confiabilidade da resolução.
    """

    api_ok = api is not None and api.bairro is not None
    inf_ok = informado.bairro is not None

    revisao_api = api is not None and api.revisao_manual

    # Caso 1: API ausente ou sem bairro utilizável
    if not api_ok:
        revisao = informado.revisao_manual or revisao_api

        if inf_ok:
            return BairroResolvido(
                bairro=informado.bairro,
                subdivisao=informado.subdivisao,
                fonte="informado",
                criterio="informado_sem_confirmacao_de_cep",
                divergencia=False,
                revisao_manual=revisao
            )

        # CORREÇÃO:
        # Nenhum bairro foi resolvido.
        # O registro deve obrigatoriamente passar por revisão manual.
        return BairroResolvido(
            bairro=None,
            subdivisao=None,
            fonte="nenhuma",
            criterio="sem_bairro_resolvido",
            divergencia=False,
            revisao_manual=True
        )

    # Caso 2: Bairro informado ausente ou não mapeado
    if not inf_ok:
        return BairroResolvido(
            bairro=api.bairro,
            subdivisao=api.subdivisao,
            fonte="api_cep",
            criterio="informado_ausente_ou_nao_mapeado_usa_api",
            divergencia=False,
            revisao_manual=revisao_api
        )

    # Caso 3: Bairro informado e API concordam
    if informado.bairro == api.bairro:
        return BairroResolvido(
            bairro=api.bairro,
            subdivisao=informado.subdivisao or api.subdivisao,
            fonte="api_cep+informado",
            criterio="concordam",
            divergencia=False,
            revisao_manual=informado.revisao_manual or revisao_api
        )

    # Caso 4: Divergência entre bairro informado e API
    return BairroResolvido(
        bairro=api.bairro,
        subdivisao=api.subdivisao,
        fonte="api_cep",
        criterio="divergencia_api_prevalece",
        divergencia=True,
        revisao_manual=informado.revisao_manual or revisao_api
    )
