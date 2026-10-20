"""ES: Este módulo declara el enrutamiento URL para el dominio de cuentas.

EN: This module declares URL routing for the accounts domain.

Contexto existente / Existing context:
URL routing for the accounts domain.
"""

from django.urls import path

from apps.accounts.views import (
    AvatarDeleteView,
    AvatarUpdateView,
    ClientInvitationAcceptView,
    ClientRegistrationDoneView,
    ClientRegistrationView,
    UserAdminPasswordView,
    UserAssignRoleView,
    UserCreateView,
    UserDetailView,
    UserListView,
    UserProfileView,
    UserRemoveRoleView,
    UserToggleActiveView,
    UserUpdateView,
    VinovaLoginView,
    VinovaLogoutView,
    VinovaPasswordResetCompleteView,
    VinovaPasswordResetConfirmView,
    VinovaPasswordResetDoneView,
    VinovaPasswordResetView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", VinovaLoginView.as_view(), name="login"),
    path("logout/", VinovaLogoutView.as_view(), name="logout"),
    path("registro/", ClientRegistrationView.as_view(), name="client_registration"),
    path("registro/revisa-tu-correo/", ClientRegistrationDoneView.as_view(), name="client_registration_done"),
    path("invitacion/<str:token>/", ClientInvitationAcceptView.as_view(), name="client_invitation_accept"),
    path("recuperar/", VinovaPasswordResetView.as_view(), name="password_reset"),
    path("recuperar/enviado/", VinovaPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("recuperar/<uidb64>/<token>/", VinovaPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("recuperar/completo/", VinovaPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("profile/avatar/", AvatarUpdateView.as_view(), name="avatar_update"),
    path("profile/avatar/delete/", AvatarDeleteView.as_view(), name="avatar_delete"),
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/new/", UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/edit/", UserUpdateView.as_view(), name="user_update"),
    path("users/<int:pk>/toggle-active/", UserToggleActiveView.as_view(), name="user_toggle_active"),
    path("users/<int:pk>/password/", UserAdminPasswordView.as_view(), name="user_admin_password"),
    path("users/<int:pk>/roles/add/", UserAssignRoleView.as_view(), name="user_assign_role"),
    path("users/<int:pk>/roles/<int:user_role_pk>/remove/", UserRemoveRoleView.as_view(), name="user_remove_role"),
]
