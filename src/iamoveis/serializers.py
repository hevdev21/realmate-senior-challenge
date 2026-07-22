from rest_framework import serializers

from .models import Mensagem


class MessageReceivedContentSerializer(serializers.Serializer):
    message_id = serializers.UUIDField()
    user_phone_number = serializers.CharField(max_length=250)
    message_content = serializers.CharField()
    timestamp = serializers.DateTimeField()


class WebhookEnvelopeSerializer(serializers.Serializer):
    event = serializers.CharField()
    content = serializers.DictField()