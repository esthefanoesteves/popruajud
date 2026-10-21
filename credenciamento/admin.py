from django.contrib import admin

from .models import DadosFaciais, Pessoa


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ["credencial", "nome_exibicao", "prioridade", "consentiu_foto", "mutirao"]
    list_filter = ["mutirao", "prioridade", "consentiu_foto"]
    search_fields = ["nome", "nome_social", "numero_credencial"]
    readonly_fields = ["numero_credencial", "token_qr", "credenciado_por", "credenciado_em"]
    filter_horizontal = ["servicos_desejados"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.credenciado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(DadosFaciais)
class DadosFaciaisAdmin(admin.ModelAdmin):
    """Os dados ficam cifrados; o painel só mostra que existem."""

    list_display = ["pessoa", "criado_em"]
    fields = ["pessoa", "criado_em"]
    readonly_fields = ["pessoa", "criado_em"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
