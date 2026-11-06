"""Reconhecimento e acesso (EAP 3.0), atendimentos em Serviços e o catálogo de serviços.

RF-08, RF-09, RF-14, RF-19; RD-04, RD-07.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from credenciamento.models import Pessoa
from mutirao.models import Mutirao, Posto

MUTIRAO_ENCERRADO = "O mutirão foi encerrado; os serviços oferecidos não mudam mais."


class IndicadorCNJ(models.TextChoices):
    """RD-07: os 15 números do relatório final do CNJ."""

    CERTIDAO_NASCIMENTO = "CERTIDAO_NASCIMENTO", "Certidão de nascimento"
    RG = "RG", "RG"
    CPF = "CPF", "CPF"
    TITULO_ELEITOR = "TITULO_ELEITOR", "Título de eleitor"
    CARTEIRA_TRABALHO = "CARTEIRA_TRABALHO", "Carteira de trabalho"
    SERVICO_MILITAR = "SERVICO_MILITAR", "Serviço militar"
    CADUNICO = "CADUNICO", "CadÚnico"
    BPC_LOAS = "BPC_LOAS", "BPC/LOAS"
    SEGURO_DESEMPREGO = "SEGURO_DESEMPREGO", "Seguro-desemprego"
    PERICIA = "PERICIA", "Perícia"
    PIS = "PIS", "PIS"
    FGTS = "FGTS", "FGTS"
    CONCILIACAO = "CONCILIACAO", "Conciliação"
    ORIENTACAO_JURIDICA = "ORIENTACAO_JURIDICA", "Orientação jurídica"
    NOVO_PROCESSO = "NOVO_PROCESSO", "Novo processo"


class ItemCatalogo(models.Model):
    """Base de Serviço e Instituição (RF-19): nome único e situação."""

    nome = models.CharField(max_length=150)
    # RN-03: o que já foi usado não se exclui, só se desativa.
    ativo = models.BooleanField(default=True)

    mensagem_nome_repetido = "Já existe um item com esse nome."

    class Meta:
        abstract = True
        ordering = ["nome"]
        # RN-02: nome único sem diferenciar maiúsculas.
        constraints = [models.UniqueConstraint(Lower("nome"), name="%(app_label)s_%(class)s_nome_unico")]

    def __str__(self):
        return self.nome

    def clean(self):
        repetido = type(self).objects.filter(nome__iexact=self.nome).exclude(pk=self.pk)
        if self.nome and repetido.exists():
            raise ValidationError({"nome": self.mensagem_nome_repetido})


class ServicoQuerySet(models.QuerySet):
    def oferecidos_em(self, mutirao):
        """RN-06: serviços com oferta válida no mutirão, para a triagem (RF-07)."""
        ofertas = OfertaServico.objects.validas().filter(mutirao=mutirao)
        return self.filter(pk__in=ofertas.values("servico"))


class Servico(ItemCatalogo):
    descricao = models.CharField(
        "descrição", max_length=200, blank=True,
        help_text="Uma frase em linguagem simples, mostrada na triagem.",
    )
    # RN-01 / RN-04: liga o serviço a um dos 15 números do relatório final (RF-16).
    indicador_cnj = models.CharField(
        "indicador do CNJ", max_length=20, choices=IndicadorCNJ.choices, blank=True,
        help_text="Em qual número do relatório final do CNJ o atendimento conta. Deixe vazio se não conta.",
    )

    mensagem_nome_repetido = "Já existe um serviço com esse nome."

    objects = ServicoQuerySet.as_manager()

    class Meta(ItemCatalogo.Meta):
        verbose_name = "serviço"
        verbose_name_plural = "serviços"

    def em_uso(self) -> bool:
        """RN-03: com oferta ou triagem, o serviço só pode ser desativado."""
        return self.ofertas.exists() or self.pessoa_set.exists()

    def tem_atendimento(self) -> bool:
        return Atendimento.objects.filter(oferta__servico=self).exists()

    def clean(self):
        super().clean()
        # RN-04: o indicador não muda depois do primeiro atendimento, para não alterar o relatório.
        if self.pk:
            anterior = Servico.objects.filter(pk=self.pk).values_list("indicador_cnj", flat=True).first()
            if anterior != self.indicador_cnj and self.tem_atendimento():
                raise ValidationError(
                    {"indicador_cnj": "O serviço já tem atendimento; o indicador do CNJ não pode mudar."}
                )


class Instituicao(ItemCatalogo):
    sigla = models.CharField(max_length=20, blank=True)

    mensagem_nome_repetido = "Já existe uma instituição com esse nome."

    class Meta(ItemCatalogo.Meta):
        verbose_name = "instituição"
        verbose_name_plural = "instituições"

    def __str__(self):
        return f"{self.nome} ({self.sigla})" if self.sigla else self.nome

    def em_uso(self) -> bool:
        """RN-03: com oferta, a instituição só pode ser desativada."""
        return self.ofertas.exists()


class OfertaQuerySet(models.QuerySet):
    def validas(self):
        """RN-06: a oferta só vale com ela, o serviço e a instituição ativos."""
        return self.filter(ativo=True, servico__ativo=True, instituicao__ativo=True)


class OfertaServico(models.Model):
    """RF-19 (UC-05): qual instituição presta qual serviço em cada mutirão."""

    mutirao = models.ForeignKey(Mutirao, on_delete=models.CASCADE, related_name="ofertas")
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name="ofertas", verbose_name="serviço")
    instituicao = models.ForeignKey(
        Instituicao, on_delete=models.PROTECT, related_name="ofertas", verbose_name="instituição"
    )
    ativo = models.BooleanField(default=True)

    objects = OfertaQuerySet.as_manager()

    class Meta:
        verbose_name = "serviço oferecido"
        verbose_name_plural = "serviços oferecidos"
        ordering = ["mutirao", "servico__nome", "instituicao__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["mutirao", "servico", "instituicao"], name="oferta_unica_no_mutirao"
            ),
        ]

    def __str__(self):
        return f"{self.servico} · {self.instituicao}"

    def em_uso(self) -> bool:
        """RN-03: oferta com atendimento só pode ser desativada."""
        return self.atendimentos.exists()

    def clean(self):
        anterior = None
        if not self._state.adding:
            anterior = (
                OfertaServico.objects.filter(pk=self.pk)
                .values("servico_id", "instituicao_id", "ativo").first()
            )
        atual = {"servico_id": self.servico_id, "instituicao_id": self.instituicao_id, "ativo": self.ativo}
        if anterior == atual:
            return
        # RN-07: mutirão encerrado não aceita mudança nas ofertas.
        if self.mutirao_id and self.mutirao.encerrado_em:
            raise ValidationError(MUTIRAO_ENCERRADO)
        erros = {}
        if self.servico_id and not self.servico.ativo and (anterior or {}).get("servico_id") != self.servico_id:
            erros["servico"] = "Serviço desativado. Reative no catálogo antes de oferecer."
        if (
            self.instituicao_id and not self.instituicao.ativo
            and (anterior or {}).get("instituicao_id") != self.instituicao_id
        ):
            erros["instituicao"] = "Instituição desativada. Reative no catálogo antes de oferecer."
        if erros:
            raise ValidationError(erros)


class Metodo(models.TextChoices):
    FACE = "FACE", "Face"
    QR = "QR", "Credencial QR"


class Resultado(models.TextChoices):
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    # RD-04: o algoritmo nunca nega sozinho; abaixo do limiar vai para o operador.
    CONFERENCIA = "CONFERENCIA", "Aguardando conferência do operador"


class Decisao(models.TextChoices):
    LIBERADO = "LIBERADO", "Liberado pelo operador"
    NAO_LIBERADO = "NAO_LIBERADO", "Não liberado pelo operador"


class RegistroAcesso(models.Model):
    """Cada passagem por um posto (RF-08), com a conferência humana quando houver (RF-14)."""

    pessoa = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name="acessos")
    posto = models.ForeignKey(Posto, on_delete=models.PROTECT, related_name="acessos")
    metodo = models.CharField(max_length=4, choices=Metodo.choices)
    resultado = models.CharField(max_length=12, choices=Resultado.choices)
    similaridade = models.FloatField(null=True, blank=True)
    decisao_operador = models.CharField(max_length=12, choices=Decisao.choices, blank=True)
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "registro de acesso"
        verbose_name_plural = "registros de acesso"
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.pessoa} em {self.posto}: {self.get_resultado_display()}"

    @property
    def liberado(self) -> bool:
        return self.resultado == Resultado.CONFIRMADO or self.decisao_operador == Decisao.LIBERADO


class Atendimento(models.Model):
    """RF-09: cada atendimento pelo serviço oferecido, que traz a instituição e o tipo de serviço."""

    pessoa = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name="atendimentos")
    posto = models.ForeignKey(Posto, on_delete=models.PROTECT, related_name="atendimentos")
    oferta = models.ForeignKey(
        OfertaServico, on_delete=models.PROTECT, related_name="atendimentos", verbose_name="serviço oferecido"
    )
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.oferta} para {self.pessoa}"

    def clean(self):
        if self.oferta_id and self.posto_id and self.oferta.mutirao_id != self.posto.mutirao_id:
            raise ValidationError({"oferta": "Esse serviço não é oferecido no mutirão deste posto."})
