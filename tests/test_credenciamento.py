import numpy as np
import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from credenciamento.models import DadosFaciais, Pessoa
from mutirao import perfis


def test_perfis_existem_apos_migracao(db):
    """RF-01: coordenação, credenciador e operador de posto."""
    assert set(Group.objects.values_list("name", flat=True)) >= set(perfis.TODOS)


def test_so_o_nome_e_obrigatorio(mutirao):
    """RNF-10 / RD-01: sem documento, sem data de nascimento, sem barreira."""
    p = Pessoa(mutirao=mutirao, nome="João")
    p.full_clean(exclude=["numero_credencial"])
    p.save()
    assert p.documento == "" and p.data_nascimento is None


def test_credencial_sequencial_por_mutirao(mutirao):
    a = Pessoa.objects.create(mutirao=mutirao, nome="A")
    b = Pessoa.objects.create(mutirao=mutirao, nome="B")
    assert (a.credencial, b.credencial) == ("0001", "0002")


def test_nome_social_prevalece(mutirao):
    """RD-05."""
    p = Pessoa.objects.create(mutirao=mutirao, nome="Registro Civil", nome_social="Nome Social")
    assert p.nome_exibicao == "Nome Social"
    assert "Nome Social" in str(p)


def test_dados_faciais_exigem_consentimento(pessoa):
    """RD-02: quem recusou a foto não tem dados faciais guardados."""
    pessoa.consentiu_foto = False
    pessoa.save()
    dados = DadosFaciais(pessoa=pessoa)
    dados.definir_foto(b"jpeg")
    dados.definir_modelo(np.ones(128, dtype=np.float32))
    with pytest.raises(ValidationError):
        dados.save()


def test_dados_faciais_cifrados_em_repouso(pessoa):
    """RNF-08: o banco guarda só o cifrado; a leitura devolve o original."""
    pessoa.consentiu_foto = True
    pessoa.save()
    foto = b"\xff\xd8 foto de referencia"
    vetor = np.arange(128, dtype=np.float32)
    dados = DadosFaciais(pessoa=pessoa)
    dados.definir_foto(foto)
    dados.definir_modelo(vetor)
    dados.save()

    salvo = DadosFaciais.objects.get(pk=dados.pk)
    assert foto not in bytes(salvo.foto_cifrada)
    assert salvo.obter_foto() == foto
    assert np.array_equal(salvo.obter_modelo().ravel(), vetor)
