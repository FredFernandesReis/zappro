from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("autorespostas", "0005_boas_vindas_audio"),
    ]

    operations = [
        migrations.AlterField(
            model_name="configuracaoboasvindas",
            name="mensagem",
            field=models.TextField(blank=True, default="", verbose_name="Mensagem 1"),
        ),
    ]
