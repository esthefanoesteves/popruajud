from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

admin.site.site_header = "PopRuaJud · Controle de Acesso"
admin.site.site_title = "PopRuaJud"
admin.site.index_title = "Gestão do mutirão"

urlpatterns = [
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
    path("admin/", admin.site.urls),
]
