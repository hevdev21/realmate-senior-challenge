from django.contrib import admin
from django.urls import include, path
from iamoveis.views import WebhookMessageView, ConversaMensagensView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("webhook/message", WebhookMessageView.as_view(), name="webhook-message"),
    path("api/conversations/<str:user_phone>/messages", ConversaMensagensView.as_view(), name="conversa-mensagens"),
]
