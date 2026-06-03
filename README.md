# Desafio Dev Sênior — Sistema de Mensageria com IA

## Contexto

A **Realmate** está construindo um assistente de IA para atendimento de clientes em uma
imobiliária. O assistente conversa com potenciais compradores e inquilinos via WhatsApp,
entende o que eles buscam e pesquisa imóveis no banco de dados para oferecer opções
compatíveis.

Você é responsável por construir o backend desse sistema.

## O que já está pronto

Antes de iniciar, verifique os arquivos fornecidos:

- `[docker-compose.yml](./docker-compose.yml)` — sobe o PostgreSQL e o Redis.
- `[Dockerfile](./Dockerfile)` — imagem Docker do backend (opcional).
- `[pyproject.toml](./pyproject.toml)` — dependências do projeto (gerenciado por **uv**).
- `[src/config/](./src/config/)` — projeto Django esqueleto com conexão ao banco
estabelecida, **sem apps criados**.
- `[data/imoveis.csv](./data/imoveis.csv)` — 10 imóveis em CSV.
- `[data/imoveis_resumo.json](./data/imoveis_resumo.json)` — 10 imóveis **diferentes**
em JSON.
- `[data/perguntas_frequentes.json](./data/perguntas_frequentes.json)` — 10 perguntas
e respostas sobre a imobiliária.

## Objetivo do Projeto

Você deve construir uma IA capaz de conversar com os clientes da imobiliária, encontrar
imóveis para eles e tirar dúvidas sobre a imobiliária. A IA deve manter uma conversa
com o cliente, buscar imóveis no banco de dados e consultar as perguntas frequentes.

Você deve construir uma aplicação Django tipada com mypy.

## Restrições na busca de imóveis

- Se o cliente informar o **código do imóvel**, a IA deve ser capaz de encontrar
diretamente.
- Se o cliente **não** tem o código, a IA só deve buscar imóveis quando tiver no mínimo os seguintes campos. Se algum desses campos não foi informado, a IA deve perguntar ao cliente antes de buscar:
  - **preço mínimo**
  - **bairro**
  - **tipo de transação** (aluguel/venda).
- A IA deve retornar **no máximo 2 imóveis por busca**. O cliente pode pedir mais
opções — nesse caso a IA busca novamente trazendo outros imóveis que ainda não
foram mostrados ao cliente.
- A IA **nunca** deve sugerir um imóvel que já foi recomendado ao cliente na mesma
conversa.
- A IA deve ser capaz de responder sobre **características do imóvel** que estão na  
descrição (ex: se aceita pets, se tem vaga de garagem, valor do condomínio). Se a  
informação não estiver disponível, ela deve responder que não sabe.

## Premissas do negócio

- Todos os imóveis são da **mesma cidade** (Recife/PE).
- Todos os imóveis e buscas são **residenciais** (não existem imóveis comerciais na base).
- O cliente pode se referir ao imóvel pelo **código** ou por **características** (bairro, preço, tipo de transação, quantidade de quartos).

## Filtros da tool de busca

A IA deve ser capaz de filtrar pelas seguintes características


| Campo           | Operador                 | Obrigatório?                           |
| --------------- | ------------------------ | -------------------------------------- |
| código          | =                        | Sim, se os demais não forem informados |
| tipo de negocio | = (aluguel / venda)      | Sim, se código não for informado       |
| bairro          | =                        | Sim, se código não for informado       |
| preço           | >=, <= (ou ambos juntos) | Sim, se código não for informado       |
| quartos         | =                        | Não                                    |


- Se o cliente fornecer código, os demais campos são dispensáveis.
- Se o cliente não fornecer código, tipo de negocio, bairro e preço mínimo são
obrigatórios.
- ela deve conseguir buscar preço mínimo, preço máximo ou uma faixa de preço.
- quartos é um filtro opcional adicional (exato).

## O que você deve construir

### 1. Modelagem do banco de dados

Modele as tabelas necessárias para representar:

- **Imóveis** — com todos os dados relevantes para busca, incluindo o código extraído
da descrição em coluna própria.
- **Conversas** — identificadas pelo telefone do cliente.
- **Mensagens** — cada interação da conversa (cliente e assistente).

Se achar necessário, você pode criar outros modelos.



### 2. Carga dos dados

Crie um sistema de carga que leia os arquivos `data/imoveis.csv` e
`data/imoveis_resumo.json`, processe e insira os imóveis no banco de dados.

Considere que:

- Ambos contêm imóveis **diferentes** — devem ser mesclados em uma única tabela.
- Novos formatos de arquivo podem surgir no futuro — sua solução deve ser extensível.
- Cargas repetidas não devem duplicar registros (idempotência), usando o código do
imóvel como chave de unicidade.
- A carga deve ser **automatizada** e executada **todos os dias às 00:00 UTC**.

### 3. Webhook para receber mensagens

O sistema recebe diferentes tipos de evento pelo mesmo endpoint. Exemplos:

```
POST /webhook/message
Content-Type: application/json

# Evento de mensagem — deve ser processado
{
  "event": "MESSAGE_RECEIVED",
  "content": {
    "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097",
    "user_phone_number": "+5581982860171",
    "message_content": "Olá, estou procurando um apartamento para alugar em Boa Viagem, até R$ 3.000",
    "timestamp": "2026-06-02T10:00:00Z"
  }
}

# Outros eventos — devem ser ignorados (apenas retornar 200 OK)
{
  "event": "MESSAGE_READ",
  "content": {
    "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097",
    "user_phone_number": "+5581982860171",
    "read_at": "2026-06-02T10:00:10Z"
  }
}
```

Regras do webhook:

- Apenas eventos com `event: "MESSAGE_RECEIVED"` devem ser processados.
- Eventos de outros tipos devem responder `200 OK` sem processamento.
- O `message_id` é um UUID que garante idempotência.
- Cada `user_phone_number` identifica uma conversa única.
- Mensagens duplicadas (mesmo `message_id`) devem ser ignoradas silenciosamente, e retornar 200.
- O processamento é **assíncrono**: o webhook deve validar e enfileirar a mensagem,  
respondendo imediatamente na view. O processamento com IA ocorre via **Celery**.
- A resposta do webhook deve seguir o formato:

```json
{
  "status": "accepted",
  "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097"
}
```



### 🚨 Debounce de mensagens

Um cliente pode enviar duas mensagens quebradas rapidamente, como por exemplo, 'Oi' e 'bom dia'. Nesses casos, mensagens enviadas em até 10s devem gerar somente um processamento por parte da IA. 

Considere que o cliente, se passou 10s e não houve uma mensagem, o cliente não enviará mais nenhuma mensagem até a resposta da IA. Não haverá race-condition nesse sentido.



### 4. Processamento com IA

Integre com a **DeepSeek** (via SDK compatível com OpenAI) para processar as
mensagens. Veja um exemplo em `[scripts/example_ia.py](./scripts/example_ia.py)`.

A IA deve:

1. Interpretar a mensagem do cliente.
2. Se tiver informações suficientes (**tipo de negócio**, **bairro** e **preço**),
  chamar a ferramenta de busca de imóveis.
3. Se o cliente fornecer **apenas o código do imóvel**, pode buscar sem os outros
  filtros.
4. Se faltarem informações, **perguntar ao cliente** antes de buscar.
5. Responder ao cliente com os imóveis encontrados de forma natural e objetiva.
6. Ao recomendar imóveis, a IA deve **excluir os que já foram mostrados** ao cliente
  em buscas anteriores na mesma conversa.

Você deve modelar as **ferramentas (tools)** que a IA pode chamar. São necessárias
pelo menos duas ferramentas:

1. **Busca de imóveis** — para encontrar imóveis no banco de dados com base nos
  filtros fornecidos pelo cliente. Deve contemplar os filtros descritos na seção
   "Filtros da tool de busca".
2. **Tirar dúvidas sobre a imobiliária** — para consultar as perguntas frequentes
  (`data/perguntas_frequentes.json`) e responder o cliente sobre regras, taxas,
   documentos e procedimentos da imobiliária.

> A escolha do formato de cada tool e da implementação concreta é sua. Leve em conta o tamanho dos dados e contexto desse desafio para escolher a abordagem.

### 5. API de saída

Implemente o endpoint público para consulta:

```
GET /api/conversations/{user_phone}/messages
```

Retorna o histórico de mensagens da conversa, ordenado da **mais antiga para a mais
recente**.

Exemplo de resposta:

```json
{
  "user_phone": "+5581982860171",
  "properties_found": ["IMV-001", "C011"],
  "messages": [
    {
      "role": "customer",
      "content": "Olá, estou procurando um apartamento para alugar em Boa Viagem, até R$ 3.000",
      "timestamp": "2026-06-02T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Olá! Temos algumas opções de apartamentos para alugar em Boa Viagem dentro desse valor. Encontrei 2 imóveis que podem atender você:\n\n1. **IMV-001** — Apartamento com 2 quartos, sala ampla, cozinha planejada e varanda. R$ 2.500/mês. Próximo ao Shopping Recife e praia. Condomínio com piscina e academia.\n\n2. **C011** — Apartamento com 2 quartos, sala ampla, cozinha planejada e área de serviço no Espinheiro. R$ 2.200/mês. Prédio com portaria 24h.\n\nGostaria de mais detalhes de algum deles ou quer que eu busque mais opções?",
      "timestamp": "2026-06-02T10:00:05Z"
    },
    {
      "role": "customer",
      "content": "Me fale mais sobre o primeiro",
      "timestamp": "2026-06-02T10:01:00Z"
    },
    {
      "role": "assistant",
      "content": "O **IMV-001** fica na Rua dos Navegantes, 150, Boa Viagem, a 3 quadras da praia. Tem 2 quartos, sala ampla, cozinha planejada e varanda. O condomínio é R$ 580/mês com piscina e academia. Aceita pets e tem 1 vaga de garagem coberta.",
      "timestamp": "2026-06-02T10:01:03Z"
    }
  ]
}
```

> Este endpoint será usado por testes automatizados para validar o comportamento
> do sistema. É muito importante que siga exatamente esse formato.

## Regras de negócio

- O sistema deve atender **múltiplos clientes simultaneamente**, cada um identificado
por seu número de telefone.
- O processamento das mensagens é **assíncrono** via **Celery**. O webhook apenas
valida o payload e enfileira o processamento.
- Se o cliente enviar **duas ou mais mensagens em até 10 segundos** (mesma conversa),
elas devem ser consolidadas e processadas como uma única mensagem. Mensagens muito
próximas podem indicar digitação fragmentada.
- A IA deve retornar **no máximo 2 imóveis por busca**. Se o cliente pedir mais
opções, a IA busca novamente, **excluindo os imóveis já recomendados** na conversa.
- Os resultados das buscas (imóveis encontrados) devem ser persistidos no banco de
dados, vinculados à conversa e à mensagem do assistente que os gerou. Toda
recomendação deve ficar registrada.
- Uma única conversa pode ter múltiplas buscas (o cliente refina os critérios).
- O histórico deve preservar a ordem cronológica das mensagens.
- A IA deve responder em **português brasileiro**.

## Critérios de avaliação

Sua solução será avaliada nos seguintes aspectos:

1. **Corretude funcional** — simularemos conversas com a IA via webhook e consultaremos o histórico pelo endpoint de saída para verificar se os filtros são respeitados, se a IA pergunta quando faltam informações, e se o retorno respeita o limite de 2 imóveis por busca.
2. **Modelagem das tools** — avaliaremos como você estruturou as ferramentas de function calling para a IA: definição dos parâmetros, descrições, tipos, e a estratégia de exclusão de imóveis já recomendados.
3. **Arquitetura Django** — avaliaremos a separação de responsabilidades entre apps, a modelagem do banco de dados, a aplicação de princípios de arquitetura, organização do código, e extensibilidade.
4. **Type safety** — avaliaremos a cobertura de tipagem com mypy no código fonte, seguindo as configurações definidas no `pyproject.toml`.

## Possíveis dúvidas

- A resposta da IA nesse desafio será somente guardada no banco de dados. Não será enviada por uma API.
- Não é necessário nenhum frontend para o desafio.
- Não é necessário criar nenhuma espécie de autenticação nas views ou no webhook.
- Considere que todos os telefones seguirão o formato '+5588999999999' (DDI + DDD + número 9 dígitos).

## Setup

```bash
cp .env.example .env
# configure DEEPSEEK_API_KEY no .env
docker compose up --build -d
```

O Docker Compose sobe 5 serviços:


| Serviço         | Descrição                                                        |
| --------------- | ---------------------------------------------------------------- |
| `app`           | Django + runserver (auto-reload ao editar `.py`)                 |
| `celery-worker` | Celery worker com watchmedo (restart automático ao editar `.py`) |
| `celery-beat`   | Agendador de tarefas                                             |
| `db`            | PostgreSQL 16                                                    |
| `redis`         | Redis 7                                                          |


### Comandos úteis

```bash
# Ver logs de um serviço
docker compose logs -f app
docker compose logs -f celery-worker

# Executar comandos Django
docker compose exec app python src/manage.py makemigrations
docker compose exec app python src/manage.py migrate
docker compose exec app python src/manage.py carregar_imoveis

# Verificar tipos
docker compose exec app uv run mypy src/

# Rebuild após alterar dependências
docker compose build --no-cache app

# Parar tudo
docker compose down
```

Boa sorte!