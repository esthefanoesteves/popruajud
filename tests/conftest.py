from datetime import date, time

import pytest
from django.contrib.auth import get_user_model

from credenciamento.models import Pessoa
from mutirao.models import Mutirao, Posto, Setor


@pytest.fixture
def operador(db):
    return get_user_model().objects.create_user("operador", password="senha-de-teste-123")


@pytest.fixture
def mutirao(db):
    return Mutirao.objects.create(
        nome="Pop Rua Jud Teste",
        local="Praça da Sé",
        data_inicio=date(2026, 11, 23),
        data_fim=date(2026, 11, 27),
        hora_abertura=time(10),
        hora_encerramento=time(16),
        cota_roupas_pessoa=2,
    )


@pytest.fixture
def posto_alimentos(mutirao):
    return Posto.objects.create(mutirao=mutirao, nome="Almoço 1", setor=Setor.ALIMENTOS)


@pytest.fixture
def posto_roupas(mutirao):
    return Posto.objects.create(mutirao=mutirao, nome="Roupas 1", setor=Setor.ROUPAS)


@pytest.fixture
def pessoa(mutirao):
    return Pessoa.objects.create(mutirao=mutirao, nome="Maria")
