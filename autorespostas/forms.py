"""
Formulários de respostas automáticas e configurações.
"""

from django import forms

from .models import AutoResposta, ConfiguracaoBoasVindas, ConfiguracaoHorario


class AutoRespostaForm(forms.ModelForm):
    """CRUD de respostas automáticas."""

    class Meta:
        model = AutoResposta
        fields = ("palavra_chave", "resposta", "status")
        widgets = {
            "palavra_chave": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: preço, horário, suporte",
            }),
            "resposta": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Texto da resposta automática",
            }),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class BoasVindasForm(forms.ModelForm):
    """Configuração das mensagens de boas-vindas (até 3 variações)."""

    class Meta:
        model = ConfiguracaoBoasVindas
        fields = ("ativo", "mensagem", "mensagem_2", "mensagem_3")
        widgets = {
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "mensagem": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Variação 1 — obrigatória se ativar",
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
        }


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
