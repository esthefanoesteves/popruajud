"""Reconhecimento e acesso (EAP 3.0) e atendimentos em Serviços.

RF-08, RF-09, RF-14; RD-04.
"""

from django.conf import settings
from django.db import models

from credenciamento.models import Pessoa
from mutirao.models import Posto


class Instituicao(models.Model):
    nome = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "instituição"
        verbose_name_plural = "instituições"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class TipoServico(models.Model):
    nome = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "tipo de serviço"
        verbose_name_plural = "tipos de serviço"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Metodo(models.TextChoices):
    FACE = "FACE", "Face"
    QR = "QR", "Credencial QR"


class Resultado(models.TextChoices):
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    # RD-04: o algoritmo nunca nega sozinho; abaixo do limiar vai para o operador.
    CONFERENCIA = "CONFERENCIA", "Aguardando conferência do operador"


class Decisao(models.TextChoices):
    LIBERADO = "LIBERADO", "Liberado pelo operador"
    NAO_LIBERADO = "NAO_LIBERADO", "Não liberado pelo operador"


class RegistroAcesso(models.Model):
    """Cada passagem por um posto (RF-08), com a conferência humana quando houver (RF-14)."""

    pessoa = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name="acessos")
    posto = models.ForeignKey(Posto, on_delete=models.PROTECT, related_name="acessos")
    metodo = models.CharField(max_length=4, choices=Metodo.choices)
    resultado = models.CharField(max_length=12, choices=Resultado.choices)
    similaridade = models.FloatField(null=True, blank=True)
    decisao_operador = models.CharField(max_length=12, choices=Decisao.choices, blank=True)
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "registro de acesso"
        verbose_name_plural = "registros de acesso"
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.pessoa} em {self.posto}: {self.get_resultado_display()}"

    @property
    def liberado(self) -> bool:
        return self.resultado == Resultado.CONFIRMADO or self.decisao_operador == Decisao.LIBERADO


class Atendimento(models.Model):
    """RF-09: cada atendimento por instituição e tipo de serviço."""

    pessoa = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name="atendimentos")
    posto = models.ForeignKey(Posto, on_delete=models.PROTECT, related_name="atendimentos")
    instituicao = models.ForeignKey(Instituicao, on_delete=models.PROTECT)
    tipo_servico = models.ForeignKey(TipoServico, on_delete=models.PROTECT)
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.tipo_servico} ({self.instituicao}) para {self.pessoa}"
