# Definições para o projeto.

## Estrutura

 - Mantive a estrutura sugerida criando o app/iamoveis dentro do src/ e dentro dele está toda lógica da aplicação, incluindo, services e tasks. Decide seguir assim pela praticidade.

## Carga de dados

 - Para carga de dados devidi criar um serviço especifico src/iamoveis/services/importar_imoveis.py esse serviço é dinâmico a ideia é que ele seja flexível e facil de adicionar um novo meio de carga apenas com poucas linhas de codigo.

 - Crei também quatro tasks.
    - executar_importacao_imoveis (Faz a carga dinâmica passando um arquivo e formato, deixei ela aqui para caso tenha necessidade de alguma carga específica)
    - importar_json (Carga padrão que vai rodar todos os dias para arquivo json)
    - importar_csv  (Carga padrão que vai rodar todos os dias para arquivo csv)
    - executar_carga_diaria (orquestrador a ideia aqui é que ele acione as tasks específicas para cada tipo de carga precisando apenas adicionar uma task nova caso surja um modelo novo)

## Webhook

 - Usando djando restframework com o padrão API View, implementei a view do WebhookMessageView seguindo o padrão do DRF som serializers para validação de dados, tambem isolei a parte de persistencia de dados para organização do projeto.

## Debounce de mensagens

- Persistência da mensagem é imediata; a task de IA é agendada com atraso
  de 10s (`apply_async(countdown=10)`).
- Ao acordar, a task só processa se ainda for a última mensagem do
  cliente na conversa — caso contrário, deixa a task da mensagem mais
  recente cuidar (que já vê o histórico acumulado). Resolve o caso de
  mensagens quebradas com um único processamento.
- Sem lock distribuído: a premissa do desafio (cliente só envia nova
  mensagem após resposta da IA) elimina a concorrência real entre tasks.

## Processamento de IA

- **Provedor**: DeepSeek API via SDK `openai` (compatível com function
  calling da OpenAI), modelo `deepseek-v4-flash`. Cliente instanciado de
  forma lazy para não quebrar processos que só importam `tasks.py` (ex:
  celery beat) sem executar a task.
- **Assíncrono**: webhook só valida, persiste e enfileira
  (`processar_mensagem_ia.delay`) — IA nunca é chamada direto na view.
  Idempotência via `Mensagem.message_id` unique + `IntegrityError`. Retry
  simples do Celery em falha de chamada à IA.
- **Tool `buscar_imoveis`**: filtros obrigatórios validados em Python puro
  antes de qualquer query (não depende do modelo obedecer). Busca por
  código usa a PK padrão do Django. Retorna no máximo 2 imóveis e já marca
  os retornados em `conversa.imoveis_recomendados`, garantindo que uma
  nova busca na mesma conversa exclua o que já foi mostrado.
- **Tool `consultar_perguntas_frequentes`**: carrega o JSON inteiro em
  memória e deixa o modelo responder com base nisso. Sem RAG/embeddings,
  pois o dataset é pequeno — evita complexidade desnecessária. Prompt
  instrui a IA a nunca inventar informação fora da base.