# Desafio Técnico — Desenvolvedor Sênior Backend

## Sistema de Mensageria com IA para Busca de Imóveis

## 1. Contexto

A **Realmate** está construindo um assistente de IA para atendimento de clientes de imobiliárias.

Esse assistente conversa com potenciais compradores e inquilinos via WhatsApp, entende o que eles estão buscando, consulta uma base de imóveis e responde com opções compatíveis. Ele também deve conseguir tirar dúvidas frequentes sobre a imobiliária, como documentos necessários, taxas, horários de atendimento e procedimentos.

Você será responsável por construir o backend desse sistema.

Este desafio simula uma parte real do tipo de problema que enfrentamos na Realmate: integrar IA, regras de negócio, mensageria, persistência, processamento assíncrono e modelagem de domínio de forma simples, sustentável e extensível.

---

## 2. O que queremos avaliar

Este desafio não avalia apenas se você consegue fazer uma feature funcionar.

Nosso foco principal é entender sua capacidade de:

- projetar uma aplicação backend de ponta a ponta;
- modelar dados e entidades de domínio;
- separar responsabilidades entre views, tasks, services, models, integrações e regras de negócio;
- decidir quais abstrações fazem sentido e quais seriam overengineering;
- construir um fluxo assíncrono com idempotência e consistência;
- desenhar tools para IA de forma segura, previsível e evolutiva;
- estruturar uma base de código que possa crescer sem precisar ser reescrita;
- justificar tecnicamente suas decisões.

Um script monolítico pode resolver o problema com os dados atuais, mas dificilmente sustentaria a evolução do produto. Ao mesmo tempo, uma arquitetura excessivamente abstrata para um domínio pequeno também pode ser um sinal ruim.

Queremos ver equilíbrio: **clareza, simplicidade, separação de responsabilidades e capacidade de evolução**.

---

## 3. Formato da Entrega

Você deve entregar:

1. Código fonte da aplicação com testes unitários.
2. Um documento `ARCHITECTURE.md` explicando suas principais decisões. (ou pequenos arquivos docs/ARCHITECTURE_XYZ.md separando os contextos)

Procure justificar as escolhas que você fez durante o desenvolvimento. Por exemplo, ao criar um serviço, detalhe qual parte do domínio ele cobre. Mostre também por que organizou os apps, models ou fluxos dessa forma e como suas decisões contribuem para a clareza, sustentabilidade e evolução do projeto.

---

## 4. O que já está pronto

Antes de iniciar, verifique os arquivos fornecidos:

- `docker-compose.yml` — sobe PostgreSQL e Redis.
- `Dockerfile` — imagem Docker do backend.
- `pyproject.toml` — dependências do projeto, gerenciado por `uv`.
- `src/config/` — projeto Django esqueleto, com conexão ao banco estabelecida, sem apps criados.
- `data/imoveis.csv` — 10 imóveis em CSV.
- `data/imoveis_resumo.json` — 10 imóveis diferentes em JSON.
- `data/perguntas_frequentes.json` — 10 perguntas e respostas sobre a imobiliária.

Esse repositório contém a configuração mínima de uma aplicação Django com containers, com banco de dados, Redis e um Celery Worker.
Você deve construir a aplicação a partir desse esqueleto. O código fonte da aplicação deve estar em `src/`.

---

## 5. Objetivo do projeto

Você deve construir uma aplicação Django capaz de:

1. Receber mensagens de clientes via webhook.
2. Persistir conversas e mensagens.
3. Processar mensagens de forma assíncrona com Celery.
4. Consolidar mensagens enviadas em sequência curta.
5. Chamar uma IA com tools.
6. Buscar imóveis no banco de dados.
7. Tirar dúvidas frequentes sobre a imobiliária.
8. Registrar quais imóveis foram recomendados em cada conversa.
9. Disponibilizar uma API para consultar o histórico da conversa.

A aplicação deve ser tipada com `mypy`. As configurações já estão no `pyproject.toml`.

---

## 6. Premissas de negócio

- Todos os imóveis são residenciais (nenhum cliente vai pedir imóveis comerciais).
- Todos os imóveis estão na cidade de Recife/PE (nenhum cliente vai pedir imóveis em outras cidades).
- O cliente pode se referir a um imóvel pelo código ou por características.
- O telefone do cliente identifica uma conversa única.
- Todos os telefones seguirão o formato `+5588999999999` (ddi + ddd + número).
- A resposta da IA deve ser persistida no banco, mas não precisa ser enviada para nenhuma API externa.
- Não é necessário frontend.
- Não é necessário autenticação nas views ou endpoints.
- A IA deve responder sempre em português brasileiro.

---

## 7. Requisitos funcionais

### 7.1 Modelagem do banco de dados

Modele as tabelas necessárias para representar, no mínimo:

#### Imóveis

A tabela de imóveis deve conter todos os dados relevantes para busca e resposta, incluindo:

- código do imóvel;
- tipo de transação: aluguel ou venda;
- bairro;
- preço;
- quantidade de quartos;
- descrição;
- demais campos que você considerar úteis;
- origem da carga, se considerar relevante.

O código do imóvel deve estar em coluna própria e deve ser único.

#### Conversas

Uma conversa deve ser identificada pelo telefone do cliente.
- telefone do cliente;
- status: 'active' ou 'closed';
- created_at;
- last_message_at (seja ela do cliente ou do assistente);
- imóveis recomendados ao longo da conversa;
- mensagens;

#### Mensagens

Cada interação da conversa deve ser persistida.

As mensagens devem armazenar, no mínimo:

- conversa;
- papel da mensagem: "customer" ou "assistant";
- conteúdo;
- timestamp;
- identificador externo da mensagem.

> Você pode criar outros modelos se achar necessário.

---

### 7.2 Carga dos dados

Crie um sistema de carga que leia os arquivos:

- `data/imoveis.csv`;
- `data/imoveis_resumo.json`.

Os dois arquivos contêm imóveis diferentes e devem ser mesclados em uma única tabela.

A carga deve respeitar as seguintes regras:

- cargas repetidas não devem duplicar registros;
- o código do imóvel deve ser usado como chave de unicidade;
- se o mesmo imóvel for carregado novamente, o registro existente deve ser atualizado ou ignorado de forma consistente;
- a carga deve ser automatizada para executar todos os dias às `00:00 UTC`.

#### Extensibilidade da carga

Nos próximos meses, a Realmate pretende suportar novos formatos de imóveis, como:

- XML de parceiros;
- APIs REST de portais imobiliários;

Sua solução deve ser desenhada para acomodar novos formatos com mudança mínima no código existente.

Não exigimos que você implemente XML ou API REST agora. Porém, queremos conseguir entender com o mínimo de esforço possível, sem duplicar código e sem refatorar completamente o código existente.

---

### 7.3 Webhook para receber mensagens

Implemente o endpoint:

```http
POST /webhook/message
Content-Type: application/json
```

O sistema receberá diferentes tipos de evento pelo mesmo endpoint.

#### Evento de mensagem

```json
{
  "event": "MESSAGE_RECEIVED",
  "content": {
    "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097",
    "user_phone_number": "+5581982860171",
    "message_content": "Olá, estou procurando um apartamento para alugar em Boa Viagem, até R$ 3.000",
    "timestamp": "2026-06-02T10:00:00Z"
  }
}
```

#### Exemplo de Evento que deve ser ignorado

```json
{
  "event": "MESSAGE_READ",
  "content": {
    "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097",
    "user_phone_number": "+5581982860171",
    "read_at": "2026-06-02T10:00:10Z"
  }
}
```

Regras:

- apenas eventos com `event: "MESSAGE_RECEIVED"` devem ser processados;
- outros eventos devem retornar `200 OK` sem processamento;
- o `message_id` é um UUID usado para idempotência;
- mensagens duplicadas devem ser ignoradas silenciosamente;
- o webhook não deve processar a IA diretamente;
- o webhook deve validar, persistir/enfileirar e responder rapidamente;
- o processamento da IA deve acontecer via Celery.

A resposta para mensagens aceitas deve seguir o formato:

```json
{
  "status": "accepted",
  "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097"
}
```

quando ignorado:

```json
{
  "status": "ignored",
  "message_id": "3287ac71-8b6b-4deb-a497-5b902676f097"
}
```


---

### 7.4 Debounce de mensagens

Um cliente pode enviar mensagens quebradas rapidamente, por exemplo:

```text
Oi
bom dia
estou procurando um apartamento
```

Mensagens enviadas em até 10 segundos na mesma conversa devem gerar apenas um processamento por parte da IA.

Considere a seguinte premissa para este desafio:

> Se passaram 10 segundos sem nova mensagem do cliente, o cliente não enviará outra mensagem até receber a resposta da IA.

Ou seja, você não precisa resolver todos os casos possíveis de race condition de um sistema real de produção.

---

### 7.5 Processamento com IA

Integre com a **OpenAI**, usando o SDK oficial. Não utilize frameworks como LangChain, LangGraph, etc.

A IA deve:

1. Interpretar a mensagem do cliente e o histórico da conversa.
2. Decidir se possui informações suficientes para buscar imóveis.
3. Chamar a tool de busca quando necessário.
4. Chamar a tool de perguntas frequentes quando necessário.
5. Perguntar ao cliente quando faltarem informações obrigatórias.
6. Responder de forma natural, objetiva.
7. Nunca recomendar novamente um imóvel já recomendado na mesma conversa.
8. Nunca inventar informações. Se não souber a resposta, deve perguntar ao cliente ou responder que não sabe.

---

## 8. Tools da IA

Você deve modelar pelo menos duas tools:

### 8.1 Tool de busca de imóveis

A IA deve conseguir buscar imóveis pelos seguintes filtros:


| Campo             | Operador        | Obrigatório?                                   |
| ----------------- | --------------- | ---------------------------------------------- |
| código            | =               | Sim, se os demais filtros não forem informados |
| tipo de transação | = aluguel/venda | Sim, se código não for informado               |
| bairro            | =               | Sim, se código não for informado               |
| preço             | >=, <= ou ambos | Sim, se código não for informado               |
| quartos           | =               | Não                                            |


Regras:

- se o cliente fornecer código, os demais campos são dispensáveis;
- se o cliente não fornecer código, `tipo de transação`, `bairro` e o preço mínimo (`<=`) são obrigatórios;
- o sistema deve suportar preço mínimo, preço máximo ou faixa de preço;
- quartos é um filtro opcional;
- a IA deve retornar no máximo 2 imóveis por busca;
- se o cliente pedir mais opções, a busca deve excluir imóveis já recomendados na conversa;
- a decisão deve estar explicada no `ARCHITECTURE.md`.

IMPORTANTE: A restrição de filtros mínimos deve ser determinística. Em hipótese alguma, a IA deve conseguir enviar imóveis se o cliente não preencheu os filtros obrigatórios.

---

### 8.2 Tool de perguntas frequentes

A IA deve conseguir responder dúvidas sobre a imobiliária usando o arquivo:

```text
data/perguntas_frequentes.json
```
- A IA não deve inventar regras da imobiliária. Se a informação não estiver disponível, ela deve responder que não sabe ou que não encontrou essa informação na base fornecida.

Você pode escolher a estratégia de implementação considerando o tamanho do dataset. A escolha deve ser justificada. Evite overengineering.


---

## 9. API de saída

Implemente o endpoint:

```http
GET /api/conversations/{user_phone}/messages
```

Ele deve retornar o histórico de mensagens da conversa, ordenado da mais antiga para a mais recente.

Formato esperado:

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
      "content": "Olá! Temos algumas opções de apartamentos para alugar em Boa Viagem dentro desse valor. Encontrei 2 imóveis que podem atender você...",
      "timestamp": "2026-06-02T10:00:05Z"
    }
  ]
}
```

Regras:

- `user_phone` deve ser o telefone da conversa;
- `properties_found` deve listar os códigos dos imóveis recomendados na conversa;
- `messages` deve conter mensagens de cliente e assistente;
- a ordenação deve ser cronológica, da mais antiga para a mais recente;
- o formato deve ser seguido exatamente, pois será usado por testes automatizados.

---

## 10. Regras de negócio consolidadas

- O sistema deve atender múltiplos clientes, cada um identificado por telefone.
- Cada telefone representa uma conversa.
- Mensagens duplicadas, identificadas pelo mesmo `message_id`, devem ser ignoradas.
- O webhook deve responder rapidamente e não deve executar a IA diretamente.
- O processamento deve ser assíncrono via Celery.
- Mensagens do mesmo cliente enviadas em até 10 segundos devem ser consolidadas.
- A IA só deve buscar imóveis quando houver dados suficientes.
- Se faltar informação obrigatória, a IA deve perguntar antes de buscar.
- A IA pode buscar diretamente se o cliente informar o código do imóvel.
- A IA deve recomendar no máximo 2 imóveis por busca.
- A IA não pode recomendar imóvel já recomendado na mesma conversa.
- Toda recomendação deve ser persistida.
- Uma conversa pode ter múltiplas buscas.
- O histórico deve preservar a ordem das mensagens.
- Informações não disponíveis sobre imóveis ou FAQ não devem ser inventadas.

---

## IMPORTANTE: Tipagem

O projeto deve passar em:

```bash
uv run mypy src/
```

Queremos ver uso consciente de tipagem, especialmente em:

- contratos das tools;
- payloads do webhook;
- services;
- parsers/importadores;
- integração com IA.

Evite ao máximo `#type: ignore` em todo o código.

## Documento `ARCHITECTURE.md`

Este documento é parte obrigatória da avaliação. É nele que você deve explicar o porquê de cada decisão tomada. Sinta-se a vontada para incluir:
- explicações de separação de domínios
- criação de serviços
- abordagens alternativas consideradas, e por que foram descartadas.

ou qualquer outra decisão que você julgue relevante.

## O que não esperamos

Não esperamos que você implemente uma arquitetura artificialmente complexa. Não queremos uma bazuca para matar uma formiga.

Você não precisa usar:

- microservices;
- event sourcing;
- CQRS;
- DDD completo e literal;
- arquitetura hexagonal rígida;
- LangChain;
- LangGraph;
- filas múltiplas;
- cache distribuído sofisticado;
- painel administrativo;
- frontend.

Você pode usar qualquer uma dessas abordagens se achar que faz sentido, mas o objetivo é que a arquitetura seja simples e faça sentido e seja proporcional ao tamanho do problema.

---

## 15. Setup

```bash
# configure OPENAI_API_KEY no .env antes
cp .env.example .env
docker compose up --build -d
```

O Docker Compose sobe os seguintes serviços:


| Serviço         | Descrição            |
| --------------- | -------------------- |
| `app`           | Django + runserver   |
| `celery-worker` | Worker Celery        |
| `celery-beat`   | Agendador de tarefas |
| `db`            | PostgreSQL           |
| `redis`         | Redis                |


### Comandos úteis

```bash
# Ver logs
docker compose logs -f app
docker compose logs -f celery-worker

# Rodar migrations
docker compose exec app python src/manage.py makemigrations
docker compose exec app python src/manage.py migrate

# Carregar imóveis
docker compose exec app python src/manage.py carregar_imoveis

# Verificar tipos
docker compose exec app uv run mypy src/

# Rodar testes
docker compose exec app uv run pytest

# Rebuild
docker compose build --no-cache app

# Parar tudo
docker compose down
```

---

## 16. Observações finais

Este desafio foi desenhado para avaliar senioridade técnica em um contexto próximo do que vivemos na Realmate.

Não existe uma única arquitetura correta.

O que queremos ver é sua capacidade de tomar decisões coerentes, implementar uma solução funcional, manter o código compreensível e explicar os trade-offs envolvidos.

Na dúvida, prefira uma solução simples, bem separada, testável e fácil de evoluir.

Boa sorte!