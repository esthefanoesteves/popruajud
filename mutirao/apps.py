from django.apps import AppConfig
from django.db.models.signals import post_migrate


class MutiraoConfig(AppConfig):
    name = "mutirao"
    verbose_name = "Gestão do mutirão"

    def ready(self):
        from .perfis import aplicar_permissoes

        post_migrate.connect(aplicar_permissoes, dispatch_uid="mutirao.aplicar_permissoes")
