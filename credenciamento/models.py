"""Credenciamento (EAP 2.0): dados mínimos, consentimento, foto, credencial QR e triagem.

RF-03 a RF-07; RD-01, RD-02, RD-05, RD-06; RNF-08, RNF-10.
"""

import uuid

import numpy as np
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from core.cripto import cifrar, decifrar
from mutirao.models import Mutirao


class Prioridade(models.TextChoices):
    """RD-06: atendimento prioritário sinalizado em todos os postos."""

    IDOSA = "IDOSA", "Pessoa idosa"
    GESTANTE = "GESTANTE", "Gestante"
    LACTANTE = "LACTANTE", "Lactante"
    DEFICIENCIA = "DEFICIENCIA", "Pessoa com deficiência"
    CRIANCA_COLO = "CRIANCA_COLO", "Com criança de colo"


class Pessoa(models.Model):
    """Pessoa credenciada. RNF-10: só o nome é obrigatório."""

    mutirao = models.ForeignKey(Mutirao, on_delete=models.PROTECT, related_name="pessoas")
    numero_credencial = models.PositiveIntegerField("credencial", editable=False)
    nome = models.CharField(max_length=150)
    # RD-05: telas e credencial usam o nome social quando informado.
    nome_social = models.CharField(max_length=150, blank=True)
    # RF-03 / RD-01: data de nascimento e documento só se a pessoa tiver.
    data_nascimento = models.DateField(null=True, blank=True)
    documento = models.CharField(max_length=30, blank=True)
    prioridade = models.CharField(max_length=20, choices=Prioridade.choices, blank=True)
    # RF-04: None = ainda não perguntado; True = aceitou a foto; False = recusou.
    consentiu_foto = models.BooleanField("consentiu a foto", null=True, blank=True)
    consentimento_em = models.DateTimeField(null=True, blank=True)
    # RF-06: o QR da credencial carrega só este token, nunca dados pessoais.
    token_qr = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # RF-07: triagem dos serviços desejados.
    servicos_desejados = models.ManyToManyField("acesso.TipoServico", blank=True)
    credenciado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    credenciado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["mutirao", "numero_credencial"]
        constraints = [
            models.UniqueConstraint(
                fields=["mutirao", "numero_credencial"], name="credencial_unica_no_mutirao"
            ),
        ]

    def __str__(self):
        return f"{self.credencial} · {self.nome_exibicao}"

    @property
    def nome_exibicao(self) -> str:
        return self.nome_social or self.nome

    @property
    def credencial(self) -> str:
        return f"{self.numero_credencial:04d}"

    def save(self, *args, **kwargs):
        if self.numero_credencial is None:
            with transaction.atomic():
                # Trava o mutirão para numerar as credenciais sem colisão.
                Mutirao.objects.select_for_update().get(pk=self.mutirao_id)
                ultimo = (
                    Pessoa.objects.filter(mutirao_id=self.mutirao_id)
                    .aggregate(m=models.Max("numero_credencial"))["m"]
                    or 0
                )
                self.numero_credencial = ultimo + 1
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


class DadosFaciais(models.Model):
    """Foto de referência e modelo facial (RF-05), cifrados em repouso (RNF-08).

    RD-02: só existe com consentimento. RF-18 / RD-08: apagados ao encerrar o mutirão.
    """

    pessoa = models.OneToOneField(Pessoa, on_delete=models.CASCADE, related_name="dados_faciais")
    foto_cifrada = models.BinaryField(editable=False)
    modelo_cifrado = models.BinaryField(editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "dados faciais"
        verbose_name_plural = "dados faciais"

    def __str__(self):
        return f"Dados faciais de {self.pessoa}"

    def clean(self):
        if self.pessoa.consentiu_foto is not True:
            raise ValidationError("Sem consentimento registrado, a foto não pode ser guardada (RD-02).")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    # Foto (JPEG ou PNG em bytes)
    def definir_foto(self, imagem: bytes) -> None:
        self.foto_cifrada = cifrar(imagem)

    def obter_foto(self) -> bytes:
        return decifrar(bytes(self.foto_cifrada))

    # Modelo facial (vetor de características do SFace)
    def definir_modelo(self, vetor: np.ndarray) -> None:
        self.modelo_cifrado = cifrar(np.asarray(vetor, dtype=np.float32).tobytes())

    def obter_modelo(self) -> np.ndarray:
        return np.frombuffer(decifrar(bytes(self.modelo_cifrado)), dtype=np.float32).reshape(1, -1)
