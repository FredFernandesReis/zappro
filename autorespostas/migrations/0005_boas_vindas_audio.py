from django.db import migrations, models
import autorespostas.models


class Migration(migrations.Migration):

    dependencies = [
        ("autorespostas", "0004_boas_vindas_variacoes"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracaoboasvindas",
            name="audio",
            field=models.FileField(
                blank=True,
                help_text="Opcional. Até 2 MB. Enviado como áudio no WhatsApp.",
                null=True,
                upload_to=autorespostas.models._audio_boas_vindas_path,
                verbose_name="Áudio de boas-vindas",
            ),
        ),
    ]
