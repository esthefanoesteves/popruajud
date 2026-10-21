"""Cria os grupos dos perfis de operador (RF-01)."""

from django.db import migrations

PERFIS = ["Coordenação", "Credenciador", "Operador de posto"]


def criar_perfis(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nome in PERFIS:
        Group.objects.get_or_create(name=nome)


def remover_perfis(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=PERFIS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("mutirao", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(criar_perfis, remover_perfis)]
