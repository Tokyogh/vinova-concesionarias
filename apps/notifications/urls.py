"""ES: Este módulo declara el enrutamiento URL para el dominio de notificaciones.

EN: This module declares URL routing for the notifications domain.

Contexto existente / Existing context:
URL routing for the notifications domain.
"""

from django.urls import path

from apps.notifications import views

app_name = "notifications_internal"

urlpatterns = [
    path("", views.InternalNotificationInboxView.as_view(), name="inbox"),
    path("sent/", views.InternalNotificationSentView.as_view(), name="sent"),
    path("compose/", views.InternalNotificationComposeView.as_view(), name="compose"),
    path("templates/", views.InternalNotificationTemplateListView.as_view(), name="templates"),
    path("templates/new/", views.InternalNotificationTemplateCreateView.as_view(), name="template_create"),
    path("templates/<int:pk>/edit/", views.InternalNotificationTemplateUpdateView.as_view(), name="template_update"),
    path("templates/<int:pk>/archive/", views.InternalNotificationTemplateArchiveView.as_view(), name="template_archive"),
    path("campaigns/", views.CampaignListView.as_view(), name="campaign_list"),
    path("campaigns/new/", views.CampaignCreateView.as_view(), name="campaign_create"),
    path("campaigns/<int:pk>/", views.CampaignDetailView.as_view(), name="campaign_detail"),
    path("campaigns/<int:pk>/calculate/", views.CampaignCalculateView.as_view(), name="campaign_calculate"),
    path("campaigns/<int:pk>/message/", views.CampaignMessageView.as_view(), name="campaign_message"),
    path("campaigns/<int:pk>/confirm/", views.CampaignConfirmView.as_view(), name="campaign_confirm"),
    path("<int:pk>/", views.InternalNotificationDetailView.as_view(), name="detail"),
    path("<int:pk>/archive/", views.InternalNotificationArchiveMessageView.as_view(), name="archive_message"),
    path("<int:pk>/archive-inbox/", views.InternalNotificationArchiveRecipientView.as_view(), name="archive_inbox"),
]
