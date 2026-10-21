"""Regras do catálogo de serviços (RF-19) que vão além de um cadastro simples."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from auditoria.models import registrar

from .models import MUTIRAO_ENCERRADO, OfertaServico


def copiar_ofertas(origem, destino, usuario) -> list[OfertaServico]:
    """UC-05 A1: traz para o destino as ofertas válidas da origem que ainda faltam nele.

    RN-06: só copia oferta válida. RN-07: destino encerrado não muda. RN-08: cada cópia vai para a auditoria.
    """
    if destino.encerrado_em:
        raise ValidationError(MUTIRAO_ENCERRADO)
    existentes = set(destino.ofertas.values_list("servico_id", "instituicao_id"))
    copiadas = []
    with transaction.atomic():
        for oferta in OfertaServico.objects.validas().filter(mutirao=origem).select_related("servico", "instituicao"):
            if (oferta.servico_id, oferta.instituicao_id) in existentes:
                continue
            nova = OfertaServico.objects.create(
                mutirao=destino, servico=oferta.servico, instituicao=oferta.instituicao
            )
            registrar(usuario, "inclusao_oferta", nova, mutirao=str(destino), copiada_de=str(origem))
            copiadas.append(nova)
    return copiadas
