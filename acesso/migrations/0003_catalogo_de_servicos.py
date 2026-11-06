"""RF-19: catálogo de serviços e instituições e a oferta por mutirão.

TipoServico passa a se chamar Servico; o atendimento passa a apontar para a oferta;
os 15 serviços do relatório do CNJ (RD-07) entram cadastrados (RN-01).
"""

import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models

INDICADORES = [
    ("CERTIDAO_NASCIMENTO", "Certidão de nascimento"),
    ("RG", "RG"),
    ("CPF", "CPF"),
    ("TITULO_ELEITOR", "Título de eleitor"),
    ("CARTEIRA_TRABALHO", "Carteira de trabalho"),
    ("SERVICO_MILITAR", "Serviço militar"),
    ("CADUNICO", "CadÚnico"),
    ("BPC_LOAS", "BPC/LOAS"),
    ("SEGURO_DESEMPREGO", "Seguro-desemprego"),
    ("PERICIA", "Perícia"),
    ("PIS", "PIS"),
    ("FGTS", "FGTS"),
    ("CONCILIACAO", "Conciliação"),
    ("ORIENTACAO_JURIDICA", "Orientação jurídica"),
    ("NOVO_PROCESSO", "Novo processo"),
]

# (nome, descrição, indicador). A coordenação pode editar nome e descrição depois.
SERVICOS_CNJ = [
    ("Certidão de nascimento", "Pedir a certidão de nascimento.", "CERTIDAO_NASCIMENTO"),
    ("RG", "Tirar a carteira de identidade.", "RG"),
    ("CPF", "Tirar ou regularizar o CPF.", "CPF"),
    ("Título de eleitor", "Tirar ou regularizar o título de eleitor.", "TITULO_ELEITOR"),
    ("Carteira de trabalho", "Tirar a carteira de trabalho.", "CARTEIRA_TRABALHO"),
    ("Serviço militar", "Regularizar a situação no serviço militar.", "SERVICO_MILITAR"),
    ("CadÚnico", "Fazer ou atualizar o Cadastro Único.", "CADUNICO"),
    ("BPC/LOAS", "Pedir o benefício de prestação continuada.", "BPC_LOAS"),
    ("Seguro-desemprego", "Pedir o seguro-desemprego.", "SEGURO_DESEMPREGO"),
    ("Perícia", "Fazer a perícia médica de um benefício.", "PERICIA"),
    ("PIS", "Consultar ou sacar o PIS.", "PIS"),
    ("FGTS", "Consultar ou sacar o FGTS.", "FGTS"),
    ("Conciliação", "Tentar um acordo num processo.", "CONCILIACAO"),
    ("Orientação jurídica", "Tirar dúvidas sobre direitos.", "ORIENTACAO_JURIDICA"),
    ("Novo processo", "Entrar com uma ação na Justiça.", "NOVO_PROCESSO"),
]


def atendimentos_para_ofertas(apps, schema_editor):
    """Cada atendimento já registrado passa a apontar para a oferta do seu mutirão."""
    Atendimento = apps.get_model("acesso", "Atendimento")
    OfertaServico = apps.get_model("acesso", "OfertaServico")
    for atendimento in Atendimento.objects.select_related("posto"):
        oferta, _ = OfertaServico.objects.get_or_create(
            mutirao_id=atendimento.posto.mutirao_id,
            servico_id=atendimento.tipo_servico_id,
            instituicao_id=atendimento.instituicao_id,
        )
        atendimento.oferta = oferta
        atendimento.save(update_fields=["oferta"])


def criar_servicos_cnj(apps, schema_editor):
    Servico = apps.get_model("acesso", "Servico")
    for nome, descricao, indicador in SERVICOS_CNJ:
        if not Servico.objects.filter(nome__iexact=nome).exists():
            Servico.objects.create(nome=nome, descricao=descricao, indicador_cnj=indicador)


def remover_servicos_cnj(apps, schema_editor):
    Servico = apps.get_model("acesso", "Servico")
    Servico.objects.filter(nome__in=[nome for nome, _, _ in SERVICOS_CNJ], ofertas__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("acesso", "0002_initial"),
        ("credenciamento", "0001_initial"),
        ("mutirao", "0002_perfis"),
    ]

    operations = [
        migrations.RenameModel(old_name="TipoServico", new_name="Servico"),
        migrations.AlterModelOptions(
            name="servico",
            options={"ordering": ["nome"], "verbose_name": "serviço", "verbose_name_plural": "serviços"},
        ),
        migrations.AlterField(model_name="servico", name="nome", field=models.CharField(max_length=150)),
        migrations.AddField(
            model_name="servico",
            name="descricao",
            field=models.CharField(
                blank=True,
                help_text="Uma frase em linguagem simples, mostrada na triagem.",
                max_length=200,
                verbose_name="descrição",
            ),
        ),
        migrations.AddField(
            model_name="servico",
            name="indicador_cnj",
            field=models.CharField(
                blank=True,
                choices=INDICADORES,
                help_text=(
                    "Em qual número do relatório final do CNJ o atendimento conta. "
                    "Deixe vazio se não conta."
                ),
                max_length=20,
                verbose_name="indicador do CNJ",
            ),
        ),
        migrations.AddField(model_name="servico", name="ativo", field=models.BooleanField(default=True)),
        migrations.AlterField(model_name="instituicao", name="nome", field=models.CharField(max_length=150)),
        migrations.AddField(
            model_name="instituicao", name="sigla", field=models.CharField(blank=True, max_length=20)
        ),
        migrations.AddField(model_name="instituicao", name="ativo", field=models.BooleanField(default=True)),
        migrations.AddConstraint(
            model_name="servico",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("nome"), name="acesso_servico_nome_unico"
            ),
        ),
        migrations.AddConstraint(
            model_name="instituicao",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("nome"), name="acesso_instituicao_nome_unico"
            ),
        ),
        migrations.CreateModel(
            name="OfertaServico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ativo", models.BooleanField(default=True)),
                (
                    "instituicao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ofertas",
                        to="acesso.instituicao",
                        verbose_name="instituição",
                    ),
                ),
                (
                    "mutirao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ofertas",
                        to="mutirao.mutirao",
                    ),
                ),
                (
                    "servico",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ofertas",
                        to="acesso.servico",
                        verbose_name="serviço",
                    ),
                ),
            ],
            options={
                "verbose_name": "serviço oferecido",
                "verbose_name_plural": "serviços oferecidos",
                "ordering": ["mutirao", "servico__nome", "instituicao__nome"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("mutirao", "servico", "instituicao"), name="oferta_unica_no_mutirao"
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="atendimento",
            name="oferta",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="atendimentos",
                to="acesso.ofertaservico",
                verbose_name="serviço oferecido",
            ),
        ),
        migrations.RunPython(atendimentos_para_ofertas, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="atendimento",
            name="oferta",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="atendimentos",
                to="acesso.ofertaservico",
                verbose_name="serviço oferecido",
            ),
        ),
        migrations.RemoveField(model_name="atendimento", name="instituicao"),
        migrations.RemoveField(model_name="atendimento", name="tipo_servico"),
        migrations.RunPython(criar_servicos_cnj, remover_servicos_cnj),
    ]
