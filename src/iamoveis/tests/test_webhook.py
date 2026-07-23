from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from iamoveis.models import Mensagem


@pytest.mark.django_db
class TestWebhookMessage:

    @patch("iamoveis.views.processar_mensagem_ia")
    def test_mensagem_duplicada_e_ignorada(self, mock_task: MagicMock) -> None:
        client = APIClient()
        payload: dict[str, object] = {
            "event": "MESSAGE_RECEIVED",
            "content": {
                "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097",
                "user_phone_number": "+5581982860171",
                "message_content": "Olá",
                "timestamp": "2026-06-02T10:00:00Z",
            },
        }

        resposta_1 = client.post("/webhook/message", payload, format="json")
        resposta_2 = client.post("/webhook/message", payload, format="json")

        assert resposta_1.data["status"] == "accepted"
        assert resposta_2.data["status"] == "ignored"
        assert Mensagem.objects.filter(
            message_id="3287ac71-8b6b-4deb-a497-5b902676f097"
        ).count() == 1

    def test_evento_nao_message_received_e_ignorado(self) -> None:
        client = APIClient()
        payload: dict[str, object] = {
            "event": "MESSAGE_READ",
            "content": {
                "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097",
                "user_phone_number": "+5581982860171",
                "read_at": "2026-06-02T10:00:10Z",
            },
        }

        resposta = client.post("/webhook/message", payload, format="json")

        assert resposta.status_code == 200
        assert resposta.data["status"] == "ignored"
        assert not Mensagem.objects.exists()