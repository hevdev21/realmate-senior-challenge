# views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import IntegrityError, transaction
from .models import Conversa, Mensagem
from .tasks import processar_mensagem_ia
from .serializers import WebhookEnvelopeSerializer, MessageReceivedContentSerializer


class WebhookMessageView(APIView):

    authentication_classes = [] 
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        envelope = WebhookEnvelopeSerializer(data=request.data)
        envelope.is_valid(raise_exception=True)

        event = envelope.validated_data["event"]
        content = envelope.validated_data["content"]

        if event != "MESSAGE_RECEIVED":
            message_id = content.get("message_id")
            return Response(
                {"status": "ignored", "message_id": message_id},
                status=status.HTTP_200_OK,
            )

        content_serializer = MessageReceivedContentSerializer(data=content)
        content_serializer.is_valid(raise_exception=True)
        dados = content_serializer.validated_data

        mensagem = self._persistir_mensagem(dados)

        if mensagem is None:
            return Response(
                {"status": "ignored", "message_id": str(dados["message_id"])},
                status=status.HTTP_200_OK,
            )

        processar_mensagem_ia.apply_async(args=[mensagem.id], countdown=10)
        
        return Response(
            {"status": "accepted", "message_id": str(dados["message_id"])},
            status=status.HTTP_200_OK,
        )

    def _persistir_mensagem(self, dados):
        try:
            with transaction.atomic():
                conversa, _ = Conversa.objects.get_or_create(
                    telefone_cliente=dados["user_phone_number"],
                    status="active",
                    defaults={"last_message_at": dados["timestamp"]},
                )

                mensagem = Mensagem.objects.create(
                    conversa=conversa,
                    message_id=dados["message_id"],
                    role="customer",
                    conteudo=dados["message_content"],
                )

                conversa.last_message_at = dados["timestamp"]
                conversa.save(update_fields=["last_message_at"])

            return mensagem

        except IntegrityError:
            return None
