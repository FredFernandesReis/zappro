# Generated manually — remove opção Comportamento (padrão fixo em settings)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("autorespostas", "0002_configuracaocomportamento"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ConfiguracaoComportamento",
        ),
    ]
