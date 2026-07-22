from django.contrib import admin
from django.urls import include, path
from iamoveis.views import WebhookMessageView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("webhook/message", WebhookMessageView.as_view(), name="webhook-message"),
]
