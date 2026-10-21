"""Perfis de operador (RF-01). Viram grupos do Django na migração inicial."""

COORDENACAO = "Coordenação"
CREDENCIADOR = "Credenciador"
OPERADOR_POSTO = "Operador de posto"

TODOS = [COORDENACAO, CREDENCIADOR, OPERADOR_POSTO]

# Permissões do painel por perfil ("app.codename"), aplicadas ao fim de cada migrate.
PERMISSOES = {
    COORDENACAO: [
        # RF-19 (UC-04 e UC-05, RN-05): catálogo de serviços e instituições e a oferta por mutirão.
        *(f"acesso.{acao}_{modelo}"
          for modelo in ("servico", "instituicao", "ofertaservico")
          for acao in ("view", "add", "change", "delete")),
        # Os serviços oferecidos ficam na tela do mutirão.
        "mutirao.view_mutirao",
        "mutirao.change_mutirao",
    ],
}


def aplicar_permissoes(**kwargs):
    """Dá aos grupos as permissões de PERMISSOES. Roda a cada post_migrate; as que ainda não existem
    entram quando o app delas terminar de migrar."""
    from django.contrib.auth.models import Group, Permission

    for perfil, codigos in PERMISSOES.items():
        grupo, _ = Group.objects.get_or_create(name=perfil)
        for codigo in codigos:
            app_label, codename = codigo.split(".")
            permissao = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if permissao:
                grupo.permissions.add(permissao)
