import json
from pathlib import Path

from django.conf import settings

from iamoveis.models import Imovel

FAQ_PATH = Path(settings.BASE_DIR) / "data" / "perguntas_frequentes.json"

_faq_cache = None


def _carregar_faq():

    global _faq_cache
    if _faq_cache is None:
        with open(FAQ_PATH, encoding="utf-8") as f:
            _faq_cache = json.load(f)
    return _faq_cache


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "buscar_imoveis",
            "description": (
                "Busca imoveis disponiveis para o cliente. "
                "Se o cliente informou o codigo do imovel (identificador numerico), "
                "use apenas o campo 'codigo'. Caso contrario, 'tipo_transacao', "
                "'bairro' e pelo menos um dos precos ('preco_min' e/ou 'preco_max') "
                "sao obrigatorios — nao invente esses valores, peca ao cliente se "
                "ele nao informou. A tool retorna no maximo 2 imoveis por chamada "
                "e ja exclui imoveis recomendados anteriormente nesta conversa."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "integer",
                        "description": "Identificador numerico exato do imovel, se o cliente souber.",
                    },
                    "tipo_transacao": {
                        "type": "string",
                        "enum": ["aluguel", "venda"],
                    },
                    "bairro": {"type": "string"},
                    "preco_min": {"type": "number", "description": "Preco minimo (piso)."},
                    "preco_max": {"type": "number", "description": "Preco maximo (teto)."},
                    "quartos": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_perguntas_frequentes",
            "description": (
                "Retorna a base completa de perguntas frequentes da imobiliaria. "
                "Use SOMENTE as informacoes retornadas aqui para responder duvidas "
                "institucionais do cliente (prazos, taxas, documentos, politicas "
                "de visita, contratos, etc). Se a resposta nao estiver nesta base, "
                "diga ao cliente que voce nao encontrou essa informacao — nunca "
                "invente uma regra da imobiliaria."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def executar_tool(nome, args, conversa):
    if nome == "buscar_imoveis":
        return _buscar_imoveis(conversa=conversa, **args)
    if nome == "consultar_perguntas_frequentes":
        return _consultar_faq()
    return {"erro": f"tool '{nome}' desconhecida"}


def _buscar_imoveis(conversa, codigo=None, tipo_transacao=None, bairro=None,
                     preco_min=None, preco_max=None, quartos=None):

    if codigo is not None:
        imovel = Imovel.objects.filter(pk=codigo).first()
        if not imovel:
            return {"encontrados": 0, "imoveis": [], "mensagem": "Codigo nao encontrado."}
        resultado = [imovel]

    else:
        # validacao deterministica das regras de negocio (8.1)
        faltantes = []
        if not tipo_transacao:
            faltantes.append("tipo_transacao")
        if not bairro:
            faltantes.append("bairro")
        if preco_min is None and preco_max is None:
            faltantes.append("preco_min ou preco_max")

        if faltantes:
            return {
                "erro": "filtros_insuficientes",
                "campos_faltantes": faltantes,
                "mensagem": (
                    "Não é possível buscar sem os filtros obrigatórios. "
                    "Peça esses dados ao cliente antes de chamar a tool novamente."
                ),
            }

        qs = Imovel.objects.filter(tipo_transacao=tipo_transacao, bairro__iexact=bairro)

        if preco_min is not None:
            qs = qs.filter(preco__gte=preco_min)
        if preco_max is not None:
            qs = qs.filter(preco__lte=preco_max)
        if quartos is not None:
            qs = qs.filter(quartos=quartos)

        ja_recomendados = conversa.imoveis_recomendados.values_list("id", flat=True)
        qs = qs.exclude(id__in=ja_recomendados).order_by("preco")

        resultado = list(qs[:2])

    if resultado:
        conversa.imoveis_recomendados.add(*resultado)

    return {
        "encontrados": len(resultado),
        "imoveis": [
            {
                "codigo": i.pk,
                "tipo_transacao": i.tipo_transacao,
                "bairro": i.bairro,
                "preco": str(i.preco),
                "quartos": i.quartos,
                "endereco": i.endereco,
            }
            for i in resultado
        ],
    }


def _consultar_faq():
    return {"perguntas_frequentes": _carregar_faq()}
