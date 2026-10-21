"""Alimentos (EAP 4.0) e roupas (EAP 5.0): cotas, entregas e estoque.

RF-10 a RF-13.
"""

from django.conf import settings
from django.db import models

from credenciamento.models import Pessoa
from mutirao.models import Mutirao, Posto


class TipoRefeicao(models.TextChoices):
    CAFE = "CAFE", "Café da manhã"
    ALMOCO = "ALMOCO", "Almoço"


class RecebimentoRefeicao(models.Model):
    """RF-11: refeições recebidas por fornecedor."""

    mutirao = models.ForeignKey(Mutirao, on_delete=models.PROTECT, related_name="recebimentos")
    fornecedor = models.CharField(max_length=150)
    tipo = models.CharField(max_length=6, choices=TipoRefeicao.choices)
    quantidade = models.PositiveIntegerField()
    data = models.DateField()
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "recebimento de refeições"
        verbose_name_plural = "recebimentos de refeições"
        ordering = ["-data", "tipo"]

    def __str__(self):
        return f"{self.quantidade} {self.get_tipo_display()} de {self.fornecedor} ({self.data:%d/%m})"


class EntregaRefeicao(models.Model):
    """RF-10: café e almoço retirados pela pessoa."""

    pessoa = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name="refeicoes")
    posto = models.ForeignKey(Posto, on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=6, choices=TipoRefeicao.choices)
    data = models.DateField()
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "entrega de refeição"
        verbose_name_plural = "entregas de refeição"
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} para {self.pessoa} ({self.data:%d/%m})"


class DoacaoRoupa(models.Model):
    """RF-13: peças doadas por doador, tipo e tamanho."""

    mutirao = models.ForeignKey(Mutirao, on_delete=models.PROTECT, related_name="doacoes")
    doador = models.CharField(max_length=150)
    tipo_peca = models.CharField("tipo de peça", max_length=60)
    tamanho = models.CharField(max_length=20)
    quantidade = models.PositiveIntegerField()
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "doação de roupa"
        verbose_name_plural = "doações de roupa"
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.quantidade} {self.tipo_peca} {self.tamanho} de {self.doador}"


class EntregaRoupa(models.Model):
    """RF-12: peças retiradas pela pessoa, com tipo e tamanho."""

    pessoa = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name="roupas")
    posto = models.ForeignKey(Posto, on_delete=models.PROTECT, related_name="+")
    tipo_peca = models.CharField("tipo de peça", max_length=60)
    tamanho = models.CharField(max_length=20)
    quantidade = models.PositiveSmallIntegerField(default=1)
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "entrega de roupa"
        verbose_name_plural = "entregas de roupa"
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.quantidade} {self.tipo_peca} {self.tamanho} para {self.pessoa}"
