from django.db import models

# Create your models here.


class Imovel(models.Model):
    TIPO_TRANSACAO_CHOICES = [
        ('aluguel', 'Aluguel'),
        ('venda', 'Venda'),
    ]
    tipo_transacao = models.CharField(max_length=10, choices=TIPO_TRANSACAO_CHOICES,  null=True, blank=True, db_index=True)
    bairro = models.CharField(max_length=250, null=True, blank=True)
    endereco = models.CharField(max_length=250, null=True, blank=True)
    preco = models.DecimalField(max_digits=12,decimal_places=2, null=True, blank=True)
    quartos = models.IntegerField(null=True, blank=True)
    descricao = models.TextField(null=True, blank=True)

    origem_carga = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Conversa(models.Model):
    STATUS_CHOICES = [
        ('active', 'Ativa'),
        ('closed', 'Fechada'),
    ]

    imoveis_recomendados = models.ManyToManyField(
        Imovel, 
        related_name='conversas',
        blank=True
    )
    telefone_cliente = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', db_index=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Mensagem(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Cliente'),
        ('assistant', 'Assistente'),
    ]

    conversa = models.ForeignKey(
        Conversa, 
        on_delete=models.CASCADE, 
        related_name='mensagens'
    )
    message_id = models.UUIDField(null=True, blank=True, unique=True, db_index=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    conteudo = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
