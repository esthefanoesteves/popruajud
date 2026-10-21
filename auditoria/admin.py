from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Somente leitura (RNF-12)."""

    list_display = ["registrado_em", "usuario", "acao", "objeto", "posto"]
    list_filter = ["acao", "posto"]
    search_fields = ["objeto"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
