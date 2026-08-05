# Generated manually for 3 welcome message variants

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("autorespostas", "0003_delete_configuracaocomportamento"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracaoboasvindas",
            name="mensagem_2",
            field=models.TextField(blank=True, default="", verbose_name="Mensagem 2"),
        ),
        migrations.AddField(
            model_name="configuracaoboasvindas",
            name="mensagem_3",
            field=models.TextField(blank=True, default="", verbose_name="Mensagem 3"),
        ),
        migrations.AddField(
            model_name="configuracaoboasvindas",
            name="ultima_variacao",
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name="Última variação enviada"
            ),
        ),
        migrations.AlterField(
            model_name="configuracaoboasvindas",
            name="mensagem",
            field=models.TextField(
                default="Olá! Seja bem-vindo.\nDigite:\n1 - Vendas\n2 - Suporte\n3 - Financeiro",
                verbose_name="Mensagem 1",
            ),
        ),
    ]
