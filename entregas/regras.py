"""Regras de entrega: cotas, bloqueio da segunda retirada e baixa no estoque.

RF-10 a RF-13 e RF-17 (cada entrega vai para a auditoria).
"""

from __future__ import annotations

from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from auditoria.models import registrar
from credenciamento.models import Pessoa

from .models import (
    DoacaoRoupa,
    EntregaRefeicao,
    EntregaRoupa,
    RecebimentoRefeicao,
    TipoRefeicao,
)


class CotaExcedida(Exception):
    """A pessoa já usou a cota. Leva a última entrega para o operador ver."""

    def __init__(self, mensagem: str, ultima_entrega=None):
        super().__init__(mensagem)
        self.ultima_entrega = ultima_entrega


def _cota_refeicao(pessoa: Pessoa, tipo: str) -> int:
    m = pessoa.mutirao
    return m.cota_cafe_dia if tipo == TipoRefeicao.CAFE else m.cota_almoco_dia


def entregar_refeicao(pessoa: Pessoa, tipo: str, posto, operador, dia: date | None = None) -> EntregaRefeicao:
    """RF-10: libera dentro da cota do dia e bloqueia a retirada além dela."""
    dia = dia or timezone.localdate()
    with transaction.atomic():
        # Trava a pessoa: dois postos não conseguem entregar a mesma cota ao mesmo tempo.
        Pessoa.objects.select_for_update().get(pk=pessoa.pk)
        do_dia = EntregaRefeicao.objects.filter(pessoa=pessoa, tipo=tipo, data=dia)
        if do_dia.count() >= _cota_refeicao(pessoa, tipo):
            ultima = do_dia.order_by("-registrado_em").first()
            nome = TipoRefeicao(tipo).label
            raise CotaExcedida(f"{nome} já retirado hoje.", ultima_entrega=ultima)
        entrega = EntregaRefeicao.objects.create(
            pessoa=pessoa, posto=posto, tipo=tipo, data=dia, operador=operador
        )
        registrar(operador, "entrega_refeicao", pessoa, posto=posto, tipo=tipo, data=dia.isoformat())
    return entrega


def entregar_roupa(pessoa: Pessoa, tipo_peca: str, tamanho: str, posto, operador, quantidade: int = 1) -> EntregaRoupa:
    """RF-12: libera dentro da cota de peças por pessoa no mutirão."""
    with transaction.atomic():
        Pessoa.objects.select_for_update().get(pk=pessoa.pk)
        ja_retirou = EntregaRoupa.objects.filter(pessoa=pessoa).aggregate(t=Sum("quantidade"))["t"] or 0
        cota = pessoa.mutirao.cota_roupas_pessoa
        if ja_retirou + quantidade > cota:
            ultima = EntregaRoupa.objects.filter(pessoa=pessoa).order_by("-registrado_em").first()
            raise CotaExcedida(f"Cota de roupas usada: {ja_retirou} de {cota} peças.", ultima_entrega=ultima)
        entrega = EntregaRoupa.objects.create(
            pessoa=pessoa, posto=posto, tipo_peca=tipo_peca, tamanho=tamanho,
            quantidade=quantidade, operador=operador,
        )
        registrar(
            operador, "entrega_roupa", pessoa, posto=posto,
            tipo_peca=tipo_peca, tamanho=tamanho, quantidade=quantidade,
        )
    return entrega


def saldo_cota_roupas(pessoa: Pessoa) -> int:
    ja_retirou = EntregaRoupa.objects.filter(pessoa=pessoa).aggregate(t=Sum("quantidade"))["t"] or 0
    return pessoa.mutirao.cota_roupas_pessoa - ja_retirou


def saldo_refeicoes(mutirao, tipo: str, dia: date) -> int:
    """RF-11: recebido no dia menos entregue no dia."""
    recebido = (
        RecebimentoRefeicao.objects.filter(mutirao=mutirao, tipo=tipo, data=dia)
        .aggregate(t=Sum("quantidade"))["t"] or 0
    )
    entregue = EntregaRefeicao.objects.filter(pessoa__mutirao=mutirao, tipo=tipo, data=dia).count()
    return recebido - entregue


def saldo_roupas(mutirao) -> dict[tuple[str, str], int]:
    """RF-13: saldo de peças por (tipo, tamanho)."""
    saldo: dict[tuple[str, str], int] = {}
    for d in DoacaoRoupa.objects.filter(mutirao=mutirao).values("tipo_peca", "tamanho").annotate(t=Sum("quantidade")):
        saldo[(d["tipo_peca"], d["tamanho"])] = d["t"]
    for e in (
        EntregaRoupa.objects.filter(pessoa__mutirao=mutirao)
        .values("tipo_peca", "tamanho").annotate(t=Sum("quantidade"))
    ):
        chave = (e["tipo_peca"], e["tamanho"])
        saldo[chave] = saldo.get(chave, 0) - e["t"]
    return saldo
