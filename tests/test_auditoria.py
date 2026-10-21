import pytest

from auditoria.models import AuditoriaImutavel, RegistroAuditoria, registrar


def test_registro_nao_pode_ser_alterado(operador):
    """RNF-12."""
    r = registrar(operador, "teste", "objeto")
    r.acao = "alterado"
    with pytest.raises(AuditoriaImutavel):
        r.save()
    with pytest.raises(AuditoriaImutavel):
        RegistroAuditoria.objects.filter(pk=r.pk).update(acao="alterado")


def test_registro_nao_pode_ser_apagado(operador):
    """RNF-12."""
    r = registrar(operador, "teste", "objeto")
    with pytest.raises(AuditoriaImutavel):
        r.delete()
    with pytest.raises(AuditoriaImutavel):
        RegistroAuditoria.objects.all().delete()
    assert RegistroAuditoria.objects.count() == 1
