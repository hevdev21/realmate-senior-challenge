from celery import Task, shared_task
from iamoveis.services.importar_imoveis import ImportadorImoveisService, ResultadoImportacao
from celery import group
from django.conf import settings
from django.utils import timezone
import logging
import json

from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCall
)
from openai import OpenAI

from typing import cast

from iamoveis.models import Mensagem, Conversa
from .ia_tools import TOOLS_SCHEMA, executar_tool

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
    return _client


@shared_task
def executar_importacao_imoveis(filepath: str, formato: str) -> ResultadoImportacao:
    service = ImportadorImoveisService()
    return service.importar(filepath, formato)


@shared_task
def importar_json() -> None:
    service = ImportadorImoveisService()
    service.importar(settings.IMOVEIS_JSON, "json")


@shared_task
def importar_csv() -> None:
    service = ImportadorImoveisService()
    service.importar(settings.IMOVEIS_CSV, "csv")


@shared_task
def executar_carga_diaria() -> None:
    logger.info("Iniciando carga diária...")
    group(
        importar_json.s(),
        importar_csv.s(),
    ).apply_async()
    logger.info("Carga diária enviada para processamento.")


MODELO_IA = "deepseek-v4-flash"

SYSTEM_PROMPT = """
Você é o assistente virtual de uma imobiliária. Responda em português,
de forma cordial e objetiva.

Regras obrigatórias:
- Para buscar imóveis, use a tool `buscar_imoveis`. Nunca invente
  imóveis, preços ou endereços que não vieram da tool.
- Se a tool `buscar_imoveis` retornar erro de filtros insuficientes,
  peça exatamente os campos faltantes ao cliente antes de tentar de novo.
- Para dúvidas sobre políticas da imobiliária (prazos, taxas, contratos,
  documentos etc.), use a tool `consultar_perguntas_frequentes`. Se a
  resposta não estiver na base retornada, diga que não encontrou essa
  informação — nunca invente uma regra da imobiliária.
"""

TOOLS: list[ChatCompletionToolParam] = cast(list[ChatCompletionToolParam], TOOLS_SCHEMA)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def processar_mensagem_ia(self: Task, mensagem_id: int) -> None:
    try:
        mensagem = Mensagem.objects.select_related("conversa").get(id=mensagem_id)
    except Mensagem.DoesNotExist:
        return

    conversa: Conversa = mensagem.conversa

    ultima_mensagem_cliente = (
        conversa.mensagens
        .filter(role="customer")
        .order_by("-timestamp", "-id")
        .first()
    )

    if ultima_mensagem_cliente is None or ultima_mensagem_cliente.pk != mensagem.pk:
        return

    historico = _montar_historico(conversa)

    system_message: ChatCompletionSystemMessageParam = {
        "role": "system",
        "content": SYSTEM_PROMPT,
    }
    messages: list[ChatCompletionMessageParam] = [system_message, *historico]

    try:
        resposta_final = _executar_conversa(messages, conversa)
    except Exception as exc:
        raise self.retry(exc=exc)

    Mensagem.objects.create(
        conversa=conversa,
        role="assistant",
        conteudo=resposta_final,
    )
    conversa.last_message_at = timezone.now()
    conversa.save(update_fields=["last_message_at"])


def _montar_historico(conversa: Conversa, limite: int = 20) -> list[ChatCompletionMessageParam]:
    mensagens = conversa.mensagens.order_by("-timestamp")[:limite]

    historico: list[ChatCompletionMessageParam] = []
    for m in reversed(list(mensagens)):
        if m.role == "customer":
            historico.append(
                cast(ChatCompletionUserMessageParam, {"role": "user", "content": m.conteudo})
            )
        else:
            historico.append(
                cast(ChatCompletionAssistantMessageParam, {"role": "assistant", "content": m.conteudo})
            )
    return historico


def _executar_conversa(
    messages: list[ChatCompletionMessageParam],
    conversa: Conversa,
    max_turnos: int = 5,
) -> str:
    client = _get_client()

    for _ in range(max_turnos):
        response = client.chat.completions.create(
            model=MODELO_IA,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content or ""

        messages.append(cast(ChatCompletionMessageParam, message.model_dump(exclude_none=True)))

        for tool_call in message.tool_calls:
            if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
                continue

            nome = tool_call.function.name
            args = cast(dict[str, object], json.loads(tool_call.function.arguments or "{}"))

            resultado = executar_tool(nome, args, conversa)

            tool_message: ChatCompletionToolMessageParam = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            }
            messages.append(tool_message)

    return "Desculpe, não consegui concluir sua solicitação no momento."
