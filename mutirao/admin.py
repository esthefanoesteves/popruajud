from django.contrib import admin

from .models import Mutirao, Posto


class PostoInline(admin.TabularInline):
    model = Posto
    extra = 0


@admin.register(Mutirao)
class MutiraoAdmin(admin.ModelAdmin):
    list_display = ["nome", "local", "data_inicio", "data_fim", "encerrado_em"]
    inlines = [PostoInline]
    readonly_fields = ["encerrado_em"]


@admin.register(Posto)
class PostoAdmin(admin.ModelAdmin):
    list_display = ["nome", "setor", "mutirao", "ativo"]
    list_filter = ["mutirao", "setor", "ativo"]
