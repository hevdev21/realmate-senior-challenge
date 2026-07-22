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