"""
Formulários de respostas automáticas e configurações.
"""

from django import forms

from .models import AutoResposta, ConfiguracaoBoasVindas, ConfiguracaoHorario

AUDIO_MAX_BYTES = 2 * 1024 * 1024
AUDIO_EXTS = {"ogg", "opus", "mp3", "m4a", "aac", "wav", "webm"}


class AutoRespostaForm(forms.ModelForm):
    """CRUD de respostas automáticas."""

    class Meta:
        model = AutoResposta
        fields = ("palavra_chave", "resposta", "status")
        widgets = {
            "palavra_chave": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: 1 | preço",
            }),
            "resposta": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Texto da resposta automática",
            }),
            "status": forms.Select(attrs={"class": "form-select"}),
        }
        help_texts = {
            "palavra_chave": (
                "Use | para aceitar mais de uma opção. "
                "Ex.: 1 | preço responde tanto “1” quanto “preço”."
            ),
        }


class BoasVindasForm(forms.ModelForm):
    """Configuração das mensagens de boas-vindas (até 3 variações + áudio)."""

    remover_audio = forms.BooleanField(
        required=False,
        label="Remover áudio atual",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = ConfiguracaoBoasVindas
        fields = ("ativo", "mensagem", "mensagem_2", "mensagem_3", "audio")
        widgets = {
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "mensagem": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Variação 1 — texto (opcional se enviar só o áudio)",
            }),
            "mensagem_2": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Variação 2 — opcional (recomendado)",
            }),
            "mensagem_3": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Variação 3 — opcional (recomendado)",
            }),
            "audio": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "audio/ogg,audio/mpeg,audio/mp4,audio/aac,audio/wav,audio/webm,.ogg,.mp3,.m4a,.opus,.aac,.wav,.webm",
            }),
        }

    def clean_audio(self):
        audio = self.cleaned_data.get("audio")
        if not audio:
            return audio
        name = getattr(audio, "name", "") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in AUDIO_EXTS:
            raise forms.ValidationError(
                "Use um áudio leve: ogg, mp3, m4a, opus, aac, wav ou webm."
            )
        if getattr(audio, "size", 0) > AUDIO_MAX_BYTES:
            raise forms.ValidationError("O áudio deve ter no máximo 2 MB.")
        return audio

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get("remover_audio") and instance.audio:
            instance.audio.delete(save=False)
            instance.audio = None
        if commit:
            instance.save()
        return instance


class HorarioForm(forms.ModelForm):
    """Configuração de horário de atendimento."""

    class Meta:
        model = ConfiguracaoHorario
        fields = ("ativo", "hora_inicial", "hora_final", "mensagem_fora_horario")
        widgets = {
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "hora_inicial": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_final": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "mensagem_fora_horario": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
        }
