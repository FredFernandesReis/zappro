"""
URLs do app accounts.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.inicio_redirect_view, name="root"),
    path("inicio/", views.inicio_redirect_view, name="inicio"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("cadastro/", views.register_view, name="register"),
    path("perfil/", views.profile_view, name="profile"),
    path("senha/alterar/", views.UserPasswordChangeView.as_view(), name="password_change"),
    path("senha/alterada/", views.password_change_done_view, name="password_change_done"),
    path("senha/recuperar/", views.UserPasswordResetView.as_view(), name="password_reset"),
    path("senha/recuperar/enviado/", views.UserPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("senha/redefinir/<uidb64>/<token>/", views.UserPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("senha/redefinida/", views.UserPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
