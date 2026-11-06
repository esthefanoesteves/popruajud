from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse

from auditoria.models import diferencas, registrar
from mutirao.models import Mutirao

from .models import Atendimento, Instituicao, OfertaServico, RegistroAcesso, Servico


class MutiraoFilter(admin.SimpleListFilter):
    """Filtra o catálogo pelo mutirão em que o item tem oferta ativa."""

    title = "mutirão"
    parameter_name = "mutirao"

    def lookups(self, request, model_admin):
        return [(m.pk, m.nome) for m in Mutirao.objects.all()]

    def queryset(self, request, queryset):
        if self.value() and self.value().isdigit():
            ofertas = OfertaServico.objects.filter(mutirao_id=self.value(), ativo=True)
            return queryset.filter(pk__in=ofertas.values(queryset.model._meta.model_name))
        return queryset


class OfertadoEmInline(admin.TabularInline):
    """"Oferecido em": onde o item do catálogo aparece, só para leitura."""

    model = OfertaServico
    extra = 0
    can_delete = False
    verbose_name_plural = "oferecido em"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CatalogoAdmin(admin.ModelAdmin):
    """Telas do catálogo (RF-19): desativar no lugar de excluir (RN-03) e auditoria em tudo (RN-08)."""

    change_form_template = "admin/acesso/catalogo_change_form.html"
    actions = ["desativar", "reativar"]
    search_fields = ["nome"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            total_ofertas_ativas=Count("ofertas", filter=Q(ofertas__ativo=True))
        )

    @admin.display(description="ofertas ativas", ordering="total_ofertas_ativas")
    def ofertas_ativas(self, obj):
        return obj.total_ofertas_ativas

    def get_readonly_fields(self, request, obj=None):
        return ["ativo"]

    # RN-03: excluir só o que nunca foi usado, um a um.
    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.em_uso():
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        acoes = super().get_actions(request)
        acoes.pop("delete_selected", None)
        return acoes

    # RN-08: auditoria
    def save_model(self, request, obj, form, change):
        antes = type(obj).objects.get(pk=obj.pk) if change else None
        super().save_model(request, obj, form, change)
        modelo = self.opts.model_name
        if not change:
            registrar(request.user, f"inclusao_{modelo}", obj)
        elif mudancas := diferencas(antes, obj, form.changed_data):
            registrar(request.user, f"alteracao_{modelo}", obj, mudancas=mudancas)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        registrar(request.user, f"exclusao_{self.opts.model_name}", obj)

    # Desativar e reativar: em lote na lista ou pelo botão no formulário.
    def _mudar_situacao(self, request, itens, ativo):
        verbo = "reativacao" if ativo else "desativacao"
        mudados = 0
        with transaction.atomic():
            for obj in itens:
                if obj.ativo == ativo:
                    continue
                obj.ativo = ativo
                obj.save(update_fields=["ativo"])
                registrar(request.user, f"{verbo}_{self.opts.model_name}", obj)
                mudados += 1
        return mudados

    @admin.action(description="Desativar selecionados", permissions=["change"])
    def desativar(self, request, queryset):
        self.message_user(request, f"Desativados: {self._mudar_situacao(request, queryset, False)}.")

    @admin.action(description="Reativar selecionados", permissions=["change"])
    def reativar(self, request, queryset):
        self.message_user(request, f"Reativados: {self._mudar_situacao(request, queryset, True)}.")

    def get_urls(self):
        nome = f"{self.opts.app_label}_{self.opts.model_name}_situacao"
        return [
            path("<path:object_id>/situacao/", self.admin_site.admin_view(self.alternar_situacao), name=nome),
        ] + super().get_urls()

    def alternar_situacao(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        obj = get_object_or_404(self.model, pk=object_id)
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
        self._mudar_situacao(request, [obj], not obj.ativo)
        self.message_user(request, f"{'Reativação' if obj.ativo else 'Desativação'} feita: “{obj}”.")
        return redirect(reverse(f"admin:{self.opts.app_label}_{self.opts.model_name}_change", args=[obj.pk]))

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "situacao_url": f"admin:{self.opts.app_label}_{self.opts.model_name}_situacao",
        }
        return super().change_view(request, object_id, form_url, extra_context)


class ServicoOfertadoEmInline(OfertadoEmInline):
    fields = ["mutirao", "instituicao", "ativo"]


class InstituicaoOfertaEmInline(OfertadoEmInline):
    fields = ["mutirao", "servico", "ativo"]
    verbose_name_plural = "serviços que presta"


@admin.register(Servico)
class ServicoAdmin(CatalogoAdmin):
    list_display = ["nome", "indicador_cnj", "ofertas_ativas", "ativo"]
    list_filter = ["ativo", "indicador_cnj", MutiraoFilter]
    fields = ["nome", "descricao", "indicador_cnj", "ativo"]
    inlines = [ServicoOfertadoEmInline]

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        # RN-04: com atendimento, o indicador do CNJ fica travado.
        if obj is not None and obj.tem_atendimento():
            campos = [*campos, "indicador_cnj"]
        return campos


@admin.register(Instituicao)
class InstituicaoAdmin(CatalogoAdmin):
    list_display = ["nome", "sigla", "ofertas_ativas", "ativo"]
    list_filter = ["ativo", MutiraoFilter]
    search_fields = ["nome", "sigla"]
    fields = ["nome", "sigla", "ativo"]
    inlines = [InstituicaoOfertaEmInline]


@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ["registrado_em", "pessoa", "posto", "metodo", "resultado", "decisao_operador"]
    list_filter = ["posto__mutirao", "posto", "metodo", "resultado"]


@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = ["registrado_em", "pessoa", "oferta", "posto"]
    list_filter = ["posto__mutirao", "oferta__instituicao", "oferta__servico"]
