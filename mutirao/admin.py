from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse

from acesso.models import OfertaServico
from acesso.regras import copiar_ofertas
from auditoria.models import diferencas, registrar

from .models import Mutirao, Posto


class PostoInline(admin.TabularInline):
    model = Posto
    extra = 0


def _encerrado(mutirao) -> bool:
    return mutirao is not None and mutirao.encerrado_em is not None


class OfertaInline(admin.TabularInline):
    """UC-05: serviços oferecidos no mutirão (RF-19).

    RN-03: o admin já bloqueia excluir oferta com atendimento (proteção da chave); resta desativar.
    """

    model = OfertaServico
    extra = 0
    fields = ["servico", "instituicao", "ativo"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        campo = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name in ("servico", "instituicao"):
            campo.label_from_instance = lambda o: str(o) if o.ativo else f"{o} (desativado)"
        return campo

    # RN-07: mutirão encerrado mostra as ofertas só para leitura.
    def has_add_permission(self, request, obj=None):
        return not _encerrado(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not _encerrado(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not _encerrado(obj) and super().has_delete_permission(request, obj)


class CopiarServicosForm(forms.Form):
    origem = forms.ModelChoiceField(queryset=Mutirao.objects.none(), label="Copiar de")

    def __init__(self, *args, destino, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["origem"].queryset = Mutirao.objects.exclude(pk=destino.pk)


@admin.register(Mutirao)
class MutiraoAdmin(admin.ModelAdmin):
    list_display = ["nome", "local", "data_inicio", "data_fim", "encerrado_em"]
    inlines = [PostoInline, OfertaInline]
    readonly_fields = ["encerrado_em"]

    # RN-08: inclusão, alteração e exclusão de ofertas vão para a auditoria.
    def save_formset(self, request, form, formset, change):
        if formset.model is not OfertaServico:
            return super().save_formset(request, form, formset, change)
        formset.save(commit=False)
        antes = OfertaServico.objects.in_bulk([obj.pk for obj, _ in formset.changed_objects])
        mutirao = str(form.instance)
        for obj in formset.deleted_objects:
            obj.delete()
            registrar(request.user, "exclusao_oferta", obj, mutirao=mutirao)
        for obj in formset.new_objects:
            obj.save()
            registrar(request.user, "inclusao_oferta", obj, mutirao=mutirao)
        for obj, campos in formset.changed_objects:
            obj.save()
            if mudancas := diferencas(antes[obj.pk], obj, campos):
                registrar(request.user, "alteracao_oferta", obj, mutirao=mutirao, mudancas=mudancas)
        formset.save_m2m()

    def get_urls(self):
        return [
            path(
                "<path:object_id>/copiar-servicos/",
                self.admin_site.admin_view(self.copiar_servicos),
                name="mutirao_mutirao_copiar_servicos",
            ),
        ] + super().get_urls()

    def copiar_servicos(self, request, object_id):
        """UC-05 A1: copia as ofertas de outro mutirão; a coordenação revisa na tela do mutirão."""
        destino = get_object_or_404(Mutirao, pk=object_id)
        if not self.has_change_permission(request, destino) or not request.user.has_perm("acesso.add_ofertaservico"):
            raise PermissionDenied
        form = CopiarServicosForm(request.POST or None, destino=destino)
        if request.method == "POST" and form.is_valid():
            origem = form.cleaned_data["origem"]
            try:
                copiadas = copiar_ofertas(origem, destino, request.user)
            except ValidationError as erro:
                self.message_user(request, erro.messages[0], messages.ERROR)
            else:
                if copiadas:
                    self.message_user(request, f"Serviços copiados de {origem}: {len(copiadas)}. Revise abaixo.")
                else:
                    self.message_user(request, f"Nenhum serviço novo para copiar de {origem}.", messages.WARNING)
            return redirect(reverse("admin:mutirao_mutirao_change", args=[destino.pk]))
        contexto = {
            **self.admin_site.each_context(request),
            "title": "Copiar serviços de outro mutirão",
            "opts": self.opts,
            "original": destino,
            "form": form,
        }
        return render(request, "admin/mutirao/mutirao/copiar_servicos.html", contexto)


@admin.register(Posto)
class PostoAdmin(admin.ModelAdmin):
    list_display = ["nome", "setor", "mutirao", "ativo"]
    list_filter = ["mutirao", "setor", "ativo"]
