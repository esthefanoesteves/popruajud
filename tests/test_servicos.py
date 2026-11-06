"""Catálogo de serviços e instituições e a oferta por mutirão (RF-19, RN-01 a RN-08)."""

from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from acesso.models import Atendimento, IndicadorCNJ, Instituicao, OfertaServico, Servico
from acesso.regras import copiar_ofertas
from auditoria.models import RegistroAuditoria
from mutirao import perfis
from mutirao.models import Mutirao, Posto, Setor

# Formulário de gestão do inline "oferecido em", que o painel sempre envia.
SEM_OFERTAS = {"ofertas-TOTAL_FORMS": 0, "ofertas-INITIAL_FORMS": 0}


@pytest.fixture
def coordenacao(db):
    usuario = get_user_model().objects.create_user("coordenacao", password="senha-de-teste-123", is_staff=True)
    usuario.groups.add(Group.objects.get(name=perfis.COORDENACAO))
    return usuario


@pytest.fixture
def painel(client, coordenacao):
    client.force_login(coordenacao)
    return client


@pytest.fixture
def cpf(db):
    return Servico.objects.get(indicador_cnj=IndicadorCNJ.CPF)


@pytest.fixture
def receita(db):
    return Instituicao.objects.create(nome="Receita Federal", sigla="RFB")


@pytest.fixture
def oferta(mutirao, cpf, receita):
    return OfertaServico.objects.create(mutirao=mutirao, servico=cpf, instituicao=receita)


@pytest.fixture
def atendimento(oferta, pessoa, operador):
    posto = Posto.objects.create(mutirao=oferta.mutirao, nome="Serviços 1", setor=Setor.SERVICOS)
    return Atendimento.objects.create(pessoa=pessoa, posto=posto, oferta=oferta, operador=operador)


def _outro_mutirao():
    return Mutirao.objects.create(
        nome="Pop Rua Jud Anterior", local="Praça da Sé",
        data_inicio=date(2026, 5, 4), data_fim=date(2026, 5, 8),
        hora_abertura=time(10), hora_encerramento=time(16), cota_roupas_pessoa=2,
    )


def _form_mutirao(mutirao, ofertas):
    """Dados do formulário do mutirão no painel, com o inline de serviços oferecidos."""
    dados = {
        "nome": mutirao.nome, "local": mutirao.local,
        "data_inicio": mutirao.data_inicio.isoformat(), "data_fim": mutirao.data_fim.isoformat(),
        "hora_abertura": "10:00", "hora_encerramento": "16:00",
        "cota_cafe_dia": mutirao.cota_cafe_dia, "cota_almoco_dia": mutirao.cota_almoco_dia,
        "cota_roupas_pessoa": mutirao.cota_roupas_pessoa,
        "postos-TOTAL_FORMS": 0, "postos-INITIAL_FORMS": 0,
        "ofertas-TOTAL_FORMS": len(ofertas),
        "ofertas-INITIAL_FORMS": sum(1 for o in ofertas if "id" in o),
    }
    for i, oferta in enumerate(ofertas):
        dados.update({f"ofertas-{i}-{campo}": valor for campo, valor in oferta.items()})
    return dados


def test_os_15_servicos_do_cnj_vem_cadastrados(db):
    """RN-01."""
    indicadores = set(Servico.objects.exclude(indicador_cnj="").values_list("indicador_cnj", flat=True))
    assert indicadores == set(IndicadorCNJ.values)


def test_nome_repetido_sem_diferenciar_maiusculas(cpf):
    """RN-02."""
    with pytest.raises(ValidationError) as erro:
        Servico(nome="cpf").full_clean()
    assert erro.value.message_dict["nome"] == ["Já existe um serviço com esse nome."]
    with pytest.raises(IntegrityError), transaction.atomic():
        Servico.objects.create(nome="cPf")


def test_servico_em_uso_so_se_desativa(painel, cpf, oferta, pessoa):
    """RN-03: com oferta ou triagem, o painel não deixa excluir; sem uso, deixa."""
    assert painel.get(f"/admin/acesso/servico/{cpf.pk}/delete/").status_code == 403
    livre = Servico.objects.create(nome="Corte de cabelo")
    assert painel.get(f"/admin/acesso/servico/{livre.pk}/delete/").status_code == 200
    pessoa.servicos_desejados.add(livre)
    assert livre.em_uso()


def test_indicador_nao_muda_depois_do_atendimento(cpf, atendimento):
    """RN-04."""
    cpf.indicador_cnj = IndicadorCNJ.RG
    with pytest.raises(ValidationError) as erro:
        cpf.full_clean()
    assert "indicador_cnj" in erro.value.message_dict


def test_indicador_muda_enquanto_nao_ha_atendimento(cpf, oferta):
    cpf.indicador_cnj = IndicadorCNJ.RG
    cpf.full_clean()


def test_coordenacao_tem_as_permissoes_do_catalogo(coordenacao):
    """RN-05: as permissões listadas existem e chegaram ao grupo."""
    for codigo in perfis.PERMISSOES[perfis.COORDENACAO]:
        assert coordenacao.has_perm(codigo), codigo


def test_oferta_so_vale_com_tudo_ativo(mutirao, cpf, receita, oferta):
    """RN-06."""
    assert list(Servico.objects.oferecidos_em(mutirao)) == [cpf]
    receita.ativo = False
    receita.save()
    assert not OfertaServico.objects.validas().exists()
    assert not Servico.objects.oferecidos_em(mutirao).exists()


def test_servico_desativado_nao_entra_em_oferta_nova(mutirao, cpf, receita):
    cpf.ativo = False
    cpf.save()
    with pytest.raises(ValidationError) as erro:
        OfertaServico(mutirao=mutirao, servico=cpf, instituicao=receita).full_clean()
    assert "servico" in erro.value.message_dict


def test_mutirao_encerrado_nao_muda_ofertas(mutirao, oferta, coordenacao):
    """RN-07."""
    mutirao.encerrado_em = timezone.now()
    mutirao.save()
    oferta.full_clean()  # sem mudança, continua válida
    oferta.ativo = False
    with pytest.raises(ValidationError):
        oferta.full_clean()
    with pytest.raises(ValidationError):
        copiar_ofertas(_outro_mutirao(), mutirao, coordenacao)


def test_crud_do_servico_pelo_painel_vai_para_a_auditoria(painel, coordenacao):
    """UC-04 e RN-08."""
    resposta = painel.post(
        "/admin/acesso/servico/add/",
        {"nome": "Corte de cabelo", "descricao": "Cortar o cabelo.", "indicador_cnj": "", **SEM_OFERTAS},
    )
    assert resposta.status_code == 302
    servico = Servico.objects.get(nome="Corte de cabelo")

    painel.post(
        f"/admin/acesso/servico/{servico.pk}/change/",
        {"nome": "Corte de cabelo e barba", "descricao": "Cortar o cabelo.", "indicador_cnj": "", **SEM_OFERTAS},
    )
    painel.post(f"/admin/acesso/servico/{servico.pk}/situacao/")
    servico.refresh_from_db()
    assert servico.nome == "Corte de cabelo e barba"
    assert not servico.ativo

    painel.post(f"/admin/acesso/servico/{servico.pk}/delete/", {"post": "yes"})
    assert not Servico.objects.filter(pk=servico.pk).exists()

    registros = RegistroAuditoria.objects.order_by("pk")
    assert [r.acao for r in registros] == [
        "inclusao_servico", "alteracao_servico", "desativacao_servico", "exclusao_servico",
    ]
    assert registros[1].detalhes["mudancas"] == {
        "nome": {"antes": "Corte de cabelo", "depois": "Corte de cabelo e barba"},
    }
    assert {r.usuario for r in registros} == {coordenacao}


def test_desativar_em_lote(painel, cpf):
    painel.post("/admin/acesso/servico/", {"action": "desativar", "_selected_action": [cpf.pk]})
    cpf.refresh_from_db()
    assert not cpf.ativo
    assert RegistroAuditoria.objects.get().acao == "desativacao_servico"


def test_servicos_oferecidos_na_tela_do_mutirao(painel, mutirao, cpf, receita):
    """UC-05 e RN-08: incluir, desativar e excluir oferta sem uso, tudo auditado."""
    url = f"/admin/mutirao/mutirao/{mutirao.pk}/change/"
    resposta = painel.post(url, _form_mutirao(mutirao, [{"servico": cpf.pk, "instituicao": receita.pk, "ativo": "on"}]))
    assert resposta.status_code == 302
    oferta = OfertaServico.objects.get(mutirao=mutirao)

    painel.post(url, _form_mutirao(mutirao, [{"id": oferta.pk, "servico": cpf.pk, "instituicao": receita.pk}]))
    oferta.refresh_from_db()
    assert not oferta.ativo

    painel.post(url, _form_mutirao(
        mutirao, [{"id": oferta.pk, "servico": cpf.pk, "instituicao": receita.pk, "DELETE": "on"}]
    ))
    assert not OfertaServico.objects.exists()
    assert list(RegistroAuditoria.objects.order_by("pk").values_list("acao", flat=True)) == [
        "inclusao_oferta", "alteracao_oferta", "exclusao_oferta",
    ]


def test_oferta_com_atendimento_nao_se_exclui_pelo_mutirao(painel, mutirao, oferta, atendimento):
    """RN-03."""
    resposta = painel.post(f"/admin/mutirao/mutirao/{mutirao.pk}/change/", _form_mutirao(mutirao, [{
        "id": oferta.pk, "servico": oferta.servico_id, "instituicao": oferta.instituicao_id,
        "ativo": "on", "DELETE": "on",
    }]))
    assert resposta.status_code == 200
    assert "objetos protegidos" in resposta.content.decode()
    assert OfertaServico.objects.filter(pk=oferta.pk).exists()


def test_copiar_ofertas_de_outro_mutirao(mutirao, cpf, receita, coordenacao):
    """UC-05 A1: copia só as ofertas válidas que faltam e registra cada cópia."""
    anterior = _outro_mutirao()
    rg = Servico.objects.get(indicador_cnj=IndicadorCNJ.RG)
    pis = Servico.objects.get(indicador_cnj=IndicadorCNJ.PIS)
    OfertaServico.objects.create(mutirao=anterior, servico=cpf, instituicao=receita)
    OfertaServico.objects.create(mutirao=anterior, servico=rg, instituicao=receita)
    OfertaServico.objects.create(mutirao=anterior, servico=pis, instituicao=receita, ativo=False)
    OfertaServico.objects.create(mutirao=mutirao, servico=cpf, instituicao=receita)

    copiadas = copiar_ofertas(anterior, mutirao, coordenacao)

    assert [o.servico for o in copiadas] == [rg]
    assert RegistroAuditoria.objects.get().acao == "inclusao_oferta"


def test_tela_de_copiar_servicos(painel, mutirao, cpf, receita):
    anterior = _outro_mutirao()
    OfertaServico.objects.create(mutirao=anterior, servico=cpf, instituicao=receita)
    url = f"/admin/mutirao/mutirao/{mutirao.pk}/copiar-servicos/"
    assert painel.get(url).status_code == 200
    assert painel.post(url, {"origem": anterior.pk}).status_code == 302
    assert mutirao.ofertas.count() == 1


def test_telas_do_catalogo_abrem(painel, mutirao, cpf, oferta):
    urls = [
        "/admin/acesso/servico/",
        f"/admin/acesso/servico/?mutirao={mutirao.pk}",
        "/admin/acesso/servico/add/",
        f"/admin/acesso/servico/{cpf.pk}/change/",
        "/admin/acesso/instituicao/",
        f"/admin/acesso/instituicao/{oferta.instituicao_id}/change/",
        f"/admin/mutirao/mutirao/{mutirao.pk}/change/",
    ]
    for url in urls:
        assert painel.get(url).status_code == 200, url
    pagina = painel.get(f"/admin/acesso/servico/{cpf.pk}/change/").content.decode()
    # RN-03: em uso, aparece Desativar e some o Excluir.
    assert "Desativar" in pagina
    assert 'class="deletelink"' not in pagina
