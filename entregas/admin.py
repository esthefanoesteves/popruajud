from django.contrib import admin

from .models import DoacaoRoupa, EntregaRefeicao, EntregaRoupa, RecebimentoRefeicao


@admin.register(RecebimentoRefeicao)
class RecebimentoRefeicaoAdmin(admin.ModelAdmin):
    list_display = ["data", "tipo", "fornecedor", "quantidade", "mutirao"]
    list_filter = ["mutirao", "tipo", "data"]
    exclude = ["registrado_por"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(DoacaoRoupa)
class DoacaoRoupaAdmin(admin.ModelAdmin):
    list_display = ["tipo_peca", "tamanho", "quantidade", "doador", "mutirao"]
    list_filter = ["mutirao", "tipo_peca", "tamanho"]
    exclude = ["registrado_por"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(EntregaRefeicao)
class EntregaRefeicaoAdmin(admin.ModelAdmin):
    """Entregas entram pelas regras de cota (entregas/regras.py), não pelo painel."""

    list_display = ["registrado_em", "tipo", "pessoa", "posto"]
    list_filter = ["pessoa__mutirao", "tipo", "data"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EntregaRoupa)
class EntregaRoupaAdmin(admin.ModelAdmin):
    list_display = ["registrado_em", "tipo_peca", "tamanho", "quantidade", "pessoa", "posto"]
    list_filter = ["pessoa__mutirao", "tipo_peca"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
