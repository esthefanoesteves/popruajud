"""Gestão do mutirão (EAP 1.0): evento, postos e cotas. RF-02."""

from django.core.exceptions import ValidationError
from django.db import models


class Setor(models.TextChoices):
    CREDENCIAMENTO = "CREDENCIAMENTO", "Credenciamento"
    SERVICOS = "SERVICOS", "Serviços"
    ALIMENTOS = "ALIMENTOS", "Alimentos"
    ROUPAS = "ROUPAS", "Roupas"


class Mutirao(models.Model):
    nome = models.CharField(max_length=120)
    local = models.CharField(max_length=200)
    data_inicio = models.DateField("início")
    data_fim = models.DateField("fim")
    hora_abertura = models.TimeField("abertura")
    hora_encerramento = models.TimeField("encerramento")
    # RF-10: a segunda retirada no mesmo dia é bloqueada, então a cota padrão é 1.
    cota_cafe_dia = models.PositiveSmallIntegerField("cota de café por dia", default=1)
    cota_almoco_dia = models.PositiveSmallIntegerField("cota de almoço por dia", default=1)
    # RF-12: definida pela coordenação antes do evento (premissa do escopo).
    cota_roupas_pessoa = models.PositiveSmallIntegerField("cota de peças de roupa por pessoa")
    # RF-18: marca o fim do tratamento dos dados faciais.
    encerrado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "mutirão"
        verbose_name_plural = "mutirões"
        ordering = ["-data_inicio"]

    def __str__(self):
        return self.nome

    def clean(self):
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "O fim não pode ser antes do início."})


class Posto(models.Model):
    mutirao = models.ForeignKey(Mutirao, on_delete=models.CASCADE, related_name="postos")
    nome = models.CharField(max_length=80)
    setor = models.CharField(max_length=20, choices=Setor.choices)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["mutirao", "setor", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["mutirao", "nome"], name="posto_nome_unico_no_mutirao"),
        ]

    def __str__(self):
        return f"{self.nome} ({self.get_setor_display()})"
