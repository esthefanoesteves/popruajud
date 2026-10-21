from django.contrib import admin

from .models import Atendimento, Instituicao, RegistroAcesso, TipoServico

admin.site.register(Instituicao)
admin.site.register(TipoServico)


@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ["registrado_em", "pessoa", "posto", "metodo", "resultado", "decisao_operador"]
    list_filter = ["posto__mutirao", "posto", "metodo", "resultado"]


@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = ["registrado_em", "pessoa", "instituicao", "tipo_servico", "posto"]
    list_filter = ["posto__mutirao", "instituicao", "tipo_servico"]
