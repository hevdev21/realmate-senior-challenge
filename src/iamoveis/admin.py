from django.contrib import admin
from .models import Imovel

# Register your models here.

@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'tipo_transacao', 
        'bairro', 
        'preco', 
        'quartos', 
        'origem_carga', 
        'created_at'
    )
    list_filter = ('tipo_transacao', 'bairro', 'quartos', 'origem_carga')
    search_fields = ('pk', 'bairro', 'endereco', 'descricao', 'origem_carga')
    ordering = ('-created_at',)
