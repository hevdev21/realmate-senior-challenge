from rest_framework import serializers
from typing import Any, cast
from .models import Mensagem, Conversa


class MessageReceivedContentSerializer(serializers.Serializer):
    message_id = serializers.UUIDField()
    user_phone_number = serializers.CharField(max_length=250)
    message_content = serializers.CharField()
    timestamp = serializers.DateTimeField()


class WebhookEnvelopeSerializer(serializers.Serializer):
    event = serializers.CharField()
    content = serializers.DictField()


class MensagemSaidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mensagem
        fields = ["role", "conteudo", "timestamp"]

    def to_representation(self, instance: Mensagem) -> dict[str, Any]:
        return {
            "role": instance.role,
            "content": instance.conteudo,
            "timestamp": instance.timestamp.isoformat().replace("+00:00", "Z"),
        }


class ConversaSaidaSerializer(serializers.Serializer):
    user_phone = serializers.CharField(source="telefone_cliente")
    properties_found = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()

    def get_properties_found(self, conversa: Conversa) -> list[str]:
        return [
            str(imovel.pk)
            for imovel in conversa.imoveis_recomendados.all().order_by("id")
        ]

    def get_messages(self, conversa: Conversa)  -> list[dict[str, Any]]:
        mensagens = conversa.mensagens.order_by("timestamp", "id")
        data = MensagemSaidaSerializer(mensagens, many=True).data
        return cast(list[dict[str, Any]], data)