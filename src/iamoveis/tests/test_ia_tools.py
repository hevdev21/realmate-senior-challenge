from typing import Any, cast

import pytest

from iamoveis.ia_tools import _buscar_imoveis
from iamoveis.models import Conversa, Imovel


@pytest.mark.django_db
class TestBuscarImoveis:

    def test_recusa_busca_sem_filtros_obrigatorios(self) -> None:
        conversa = Conversa.objects.create(telefone_cliente="+5581999999999")

        Imovel.objects.create(
            tipo_transacao="aluguel",
            bairro="Boa Viagem",
            endereco="Rua X, 123",
            preco=2500,
            quartos=2,
        )

        resultado = cast(dict[str, Any], _buscar_imoveis(conversa=conversa))

        assert "erro" in resultado
        assert resultado["erro"] == "filtros_insuficientes"
        assert "tipo_transacao" in resultado["campos_faltantes"]
        assert "bairro" in resultado["campos_faltantes"]

    def test_busca_com_filtros_completos_retorna_imovel(self) -> None:
        conversa = Conversa.objects.create(telefone_cliente="+5581999999999")

        Imovel.objects.create(
            tipo_transacao="aluguel",
            bairro="Boa Viagem",
            endereco="Rua X, 123",
            preco=2500,
            quartos=2,
        )

        resultado = cast(dict[str, Any], _buscar_imoveis(
            conversa=conversa,
            tipo_transacao="aluguel",
            bairro="Boa Viagem",
            preco_max=3000,
        ))

        assert resultado["encontrados"] == 1
        assert resultado["imoveis"][0]["bairro"] == "Boa Viagem"

    def test_busca_por_codigo_dispensa_demais_filtros(self) -> None:
        conversa = Conversa.objects.create(telefone_cliente="+5581999999999")

        imovel = Imovel.objects.create(
            tipo_transacao="venda",
            bairro="Casa Forte",
            endereco="Rua Y, 456",
            preco=500000,
            quartos=3,
        )

        resultado = cast(dict[str, Any], _buscar_imoveis(conversa=conversa, codigo=imovel.pk))

        assert resultado["encontrados"] == 1