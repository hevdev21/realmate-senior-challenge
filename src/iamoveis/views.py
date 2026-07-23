# views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView, Request
from rest_framework.permissions import AllowAny
from rest_framework.authentication import BaseAuthentication
from django.db import IntegrityError, transaction
from .models import Conversa, Mensagem
from .tasks import processar_mensagem_ia
from .serializers import WebhookEnvelopeSerializer, MessageReceivedContentSerializer, ConversaSaidaSerializer
from typing import TypedDict
from uuid import UUID
from datetime import datetime


class MessageReceivedContent(TypedDict):
    message_id: UUID
    user_phone_number: str
    message_content: str
    timestamp: datetime


class WebhookMessageView(APIView):

    authentication_classes: list[type[BaseAuthentication]] = [] 
    permission_classes = [AllowAny]

    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
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

        processar_mensagem_ia.apply_async(args=(mensagem.pk,), countdown=10)
        
        return Response(
            {"status": "accepted", "message_id": str(dados["message_id"])},
            status=status.HTTP_200_OK,
        )

    def _persistir_mensagem(self, dados: MessageReceivedContent) -> Mensagem | None:
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


class ConversaMensagensView(APIView):

    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]

    def get(self, request: Request, user_phone: str, *args: object, **kwargs: object) -> Response:
        conversa = (
            Conversa.objects
            .filter(telefone_cliente=user_phone)
            .order_by("-created_at")
            .first()
        )

        if conversa is None:
            return Response(
                {"detail": "Conversa não encontrada para este telefone."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConversaSaidaSerializer(conversa)
        return Response(serializer.data, status=status.HTTP_200_OK)