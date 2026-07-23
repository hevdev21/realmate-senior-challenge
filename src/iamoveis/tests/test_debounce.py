from unittest.mock import MagicMock, patch

import pytest

from iamoveis.models import Conversa, Mensagem
from iamoveis.tasks import processar_mensagem_ia


@pytest.mark.django_db
class TestDebounce:

    @patch("iamoveis.tasks._executar_conversa")
    def test_nao_processa_se_nao_for_a_ultima_mensagem(
        self, mock_executar: MagicMock
    ) -> None:
        conversa = Conversa.objects.create(telefone_cliente="+5581999999999")

        mensagem_antiga = Mensagem.objects.create(
            conversa=conversa, role="customer", conteudo="Oi",
        )
        Mensagem.objects.create(
            conversa=conversa, role="customer", conteudo="bom dia",
        )

        processar_mensagem_ia(mensagem_antiga.pk)

        mock_executar.assert_not_called()

    @patch("iamoveis.tasks._executar_conversa", return_value="resposta da IA")
    def test_processa_se_for_a_ultima_mensagem(
        self, mock_executar: MagicMock
    ) -> None:
        conversa = Conversa.objects.create(telefone_cliente="+5581999999999")

        mensagem = Mensagem.objects.create(
            conversa=conversa, role="customer", conteudo="estou procurando apto",
        )

        processar_mensagem_ia(mensagem.pk)

        mock_executar.assert_called_once()
        assert conversa.mensagens.filter(role="assistant").count() == 1