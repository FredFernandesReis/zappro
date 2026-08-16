"""
Formulários de autenticação e perfil.
"""

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User

from .models import UserProfile


class LoginForm(AuthenticationForm):
    """Formulário de login com estilo Bootstrap."""

    username = forms.CharField(
        label="Usuário ou E-mail",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Digite seu usuário",
            "autocomplete": "username",
            "autofocus": True,
        }),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Digite sua senha",
            "autocomplete": "current-password",
        }),
    )


class RegisterForm(UserCreationForm):
    """Cadastro de novos usuários."""

    email = forms.EmailField(
        label="E-mail",
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "voce@empresa.com",
            "autocomplete": "email",
        }),
    )
    first_name = forms.CharField(
        label="Nome",
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Seu nome",
            "autocomplete": "given-name",
        }),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Seu sobrenome",
            "autocomplete": "family-name",
        }),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Escolha um nome de usuário",
            "autocomplete": "username",
        })
        self.fields["password1"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Crie uma senha segura",
            "autocomplete": "new-password",
        })
        self.fields["password2"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Digite a senha novamente",
            "autocomplete": "new-password",
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            UserProfile.objects.get_or_create(user=user)
        return user


class ProfileForm(forms.ModelForm):
    """Edição de dados do perfil."""

    first_name = forms.CharField(
        label="Nome",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = UserProfile
        fields = ("telefone", "empresa")
        widgets = {
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "empresa": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name
        self.fields["email"].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.email = self.cleaned_data["email"]
        self.user.save()
        if commit:
            profile.save()
        return profile


class CustomPasswordChangeForm(PasswordChangeForm):
    """Alteração de senha com classes Bootstrap."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class CustomPasswordResetForm(PasswordResetForm):
    """Recuperação de senha."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Seu e-mail cadastrado"}
        )


class CustomSetPasswordForm(SetPasswordForm):
    """Definição de nova senha após reset."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
