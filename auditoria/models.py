"""Trilha de auditoria (RF-17): quem fez, o quê, quando e em qual posto.

RNF-12: somente inclusão. Nem o operador nem o código podem editar ou apagar.
"""

from django.conf import settings
from django.db import models

from mutirao.models import Posto


class AuditoriaImutavel(Exception):
    pass


class _ConsultaSomenteInclusao(models.QuerySet):
    def update(self, **kwargs):
        raise AuditoriaImutavel("Registros de auditoria não podem ser alterados (RNF-12).")

    def delete(self):
        raise AuditoriaImutavel("Registros de auditoria não podem ser apagados (RNF-12).")


class RegistroAuditoria(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    acao = models.CharField("ação", max_length=60)
    objeto = models.CharField(max_length=200)
    posto = models.ForeignKey(Posto, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    detalhes = models.JSONField(default=dict, blank=True)
    registrado_em = models.DateTimeField(auto_now_add=True)

    objects = _ConsultaSomenteInclusao.as_manager()

    class Meta:
        verbose_name = "registro de auditoria"
        verbose_name_plural = "registros de auditoria"
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.registrado_em:%d/%m %H:%M} {self.usuario} {self.acao} {self.objeto}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise AuditoriaImutavel("Registros de auditoria não podem ser alterados (RNF-12).")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditoriaImutavel("Registros de auditoria não podem ser apagados (RNF-12).")


def registrar(usuario, acao: str, objeto, posto=None, **detalhes) -> RegistroAuditoria:
    return RegistroAuditoria.objects.create(
        usuario=usuario, acao=acao, objeto=str(objeto)[:200], posto=posto, detalhes=detalhes
    )
