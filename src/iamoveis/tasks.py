from celery import shared_task
from iamoveis.services.importar_imoveis import ImportadorImoveisService
from celery import group
from django.conf import settings
from django.utils import timezone
import logging
import json

from openai import OpenAI

from iamoveis.models import Mensagem
from .ia_tools import TOOLS_SCHEMA, executar_tool

logger = logging.getLogger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
    return _client

@shared_task
def executar_importacao_imoveis(filepath, formato):
    service = ImportadorImoveisService()
    return service.importar(filepath, formato)


@shared_task
def importar_json():
    service = ImportadorImoveisService()
    service.importar(settings.IMOVEIS_JSON, "json")


@shared_task
def importar_csv():
    service = ImportadorImoveisService()
    service.importar(settings.IMOVEIS_CSV, "csv")

@shared_task
def executar_carga_diaria():
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

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def processar_mensagem_ia(self, mensagem_id):
    try:
        mensagem = Mensagem.objects.select_related("conversa").get(id=mensagem_id)
    except Mensagem.DoesNotExist:
        return

    conversa = mensagem.conversa
    historico = _montar_historico(conversa)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *historico]

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


def _montar_historico(conversa, limite=20):
    role_map = {"customer": "user", "assistant": "assistant"}
    mensagens = conversa.mensagens.order_by("-timestamp")[:limite]
    return [
        {"role": role_map[m.role], "content": m.conteudo}
        for m in reversed(mensagens)
    ]


def _executar_conversa(messages, conversa, max_turnos=5):
    client = _get_client()
    for _ in range(max_turnos):
        response = client.chat.completions.create(
            model=MODELO_IA,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        messages.append(message)

        for tool_call in message.tool_calls:
            nome = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            resultado = executar_tool(nome, args, conversa)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            })

    return "Desculpe, não consegui concluir sua solicitação no momento. Um atendente vai te ajudar em breve."
