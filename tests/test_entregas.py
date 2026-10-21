from datetime import date

import pytest

from auditoria.models import RegistroAuditoria
from entregas.models import DoacaoRoupa, RecebimentoRefeicao, TipoRefeicao
from entregas.regras import (
    CotaExcedida,
    entregar_refeicao,
    entregar_roupa,
    saldo_cota_roupas,
    saldo_refeicoes,
    saldo_roupas,
)

DIA = date(2026, 11, 23)


def test_segunda_retirada_do_almoco_e_bloqueada(pessoa, posto_alimentos, operador):
    """RF-10."""
    primeira = entregar_refeicao(pessoa, TipoRefeicao.ALMOCO, posto_alimentos, operador, DIA)
    with pytest.raises(CotaExcedida) as erro:
        entregar_refeicao(pessoa, TipoRefeicao.ALMOCO, posto_alimentos, operador, DIA)
    assert erro.value.ultima_entrega == primeira


def test_cafe_nao_conta_na_cota_do_almoco(pessoa, posto_alimentos, operador):
    entregar_refeicao(pessoa, TipoRefeicao.ALMOCO, posto_alimentos, operador, DIA)
    entregar_refeicao(pessoa, TipoRefeicao.CAFE, posto_alimentos, operador, DIA)


def test_cota_renova_no_dia_seguinte(pessoa, posto_alimentos, operador):
    entregar_refeicao(pessoa, TipoRefeicao.ALMOCO, posto_alimentos, operador, DIA)
    entregar_refeicao(pessoa, TipoRefeicao.ALMOCO, posto_alimentos, operador, date(2026, 11, 24))


def test_baixa_no_estoque_de_refeicoes(mutirao, pessoa, posto_alimentos, operador):
    """RF-11."""
    RecebimentoRefeicao.objects.create(
        mutirao=mutirao, fornecedor="ABCP", tipo=TipoRefeicao.ALMOCO,
        quantidade=100, data=DIA, registrado_por=operador,
    )
    entregar_refeicao(pessoa, TipoRefeicao.ALMOCO, posto_alimentos, operador, DIA)
    assert saldo_refeicoes(mutirao, TipoRefeicao.ALMOCO, DIA) == 99


def test_cota_de_roupas_por_pessoa(pessoa, posto_roupas, operador):
    """RF-12: cota de 2 peças no mutirão de teste."""
    entregar_roupa(pessoa, "agasalho", "M", posto_roupas, operador)
    assert saldo_cota_roupas(pessoa) == 1
    entregar_roupa(pessoa, "calça", "40", posto_roupas, operador)
    with pytest.raises(CotaExcedida):
        entregar_roupa(pessoa, "meia", "U", posto_roupas, operador)


def test_baixa_no_estoque_de_roupas(mutirao, pessoa, posto_roupas, operador):
    """RF-13."""
    DoacaoRoupa.objects.create(
        mutirao=mutirao, doador="BibliASPA", tipo_peca="agasalho", tamanho="M",
        quantidade=10, registrado_por=operador,
    )
    entregar_roupa(pessoa, "agasalho", "M", posto_roupas, operador)
    assert saldo_roupas(mutirao)[("agasalho", "M")] == 9


def test_toda_entrega_vai_para_a_auditoria(pessoa, posto_alimentos, operador):
    """RF-17."""
    entregar_refeicao(pessoa, TipoRefeicao.CAFE, posto_alimentos, operador, DIA)
    registro = RegistroAuditoria.objects.get()
    assert (registro.usuario, registro.acao, registro.posto) == (operador, "entrega_refeicao", posto_alimentos)
