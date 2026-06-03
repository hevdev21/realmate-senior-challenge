# Exemplo de integração com DeepSeek via SDK compatível com OpenAI
#
# Uso:
#   1. Configure DEEPSEEK_API_KEY no .env
#   2. uv run python scripts/example_ia.py

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "Você é um assistente de imobiliária que ajuda a encontrar imóveis."},
        {"role": "user", "content": "Quero um apartamento para alugar em Boa Viagem até R$ 3.000"},
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)

print(response.choices[0].message.content)
# >>> Olá! Tudo bem? Temos...