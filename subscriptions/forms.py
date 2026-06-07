"""
Formulários de gerenciamento de assinaturas (admin).
"""

from django import forms
from django.contrib.auth.models import User

from .models import Plan, Subscription


class SubscriptionAdminForm(forms.ModelForm):
    """Formulário para admin editar assinaturas."""

    class Meta:
        model = Subscription
        fields = ("user", "plan", "status", "data_vencimento")
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "plan": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "data_vencimento": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }


class UserSubscriptionForm(forms.ModelForm):
    """Formulário simplificado para edição no painel admin."""

    class Meta:
        model = Subscription
        fields = ("plan", "status", "data_vencimento")
        widgets = {
            "plan": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "data_vencimento": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }
