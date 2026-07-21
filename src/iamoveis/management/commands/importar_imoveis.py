import csv
import json
import re
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from iamoveis.models import Imovel


class Command(BaseCommand):
    help = 'Importa imóveis a partir de arquivos CSV ou JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filepath', 
            type=str, 
            required=True, 
            help='Caminho completo para o arquivo (CSV ou JSON)'
        )
        parser.add_argument(
            '--format', 
            type=str, 
            choices=['csv', 'json'], 
            required=True, 
            help='Formato do arquivo de entrada: csv ou json'
        )

    def handle(self, *args, **options):
        filepath = options['filepath']
        fmt = options['format'].lower()
        self.stdout.write(self.style.WARNING(f"Iniciando importação do arquivo: {filepath}"))

        try:
            if fmt == 'csv':
                imoveis_data = self._parse_csv(filepath)
            else:
                imoveis_data = self._parse_json(filepath)

            self._salvar_imoveis(imoveis_data, origem_formato=fmt)

        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado no caminho: {filepath}")
        except Exception as e:
            raise CommandError(f"Erro ao processar a carga de dados: {str(e)}")

    def _parse_csv(self, filepath):
        dados = []
        with open(filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                dados.append({
                    'tipo_transacao': row.get('tipo_negocio', '').strip(),
                    'preco': Decimal(row.get('preco', 0)),
                    'quartos': int(row.get('quartos', 0)),
                    'bairro': row.get('bairro', '').strip(),
                    'endereco': row.get('endereco', '').strip(),
                    'descricao': row.get('descricao', '').strip(),
                })
        return dados

    def _parse_json(self, filepath):
        dados = []
        with open(filepath, mode='r', encoding='utf-8') as file:
            data = json.load(file)
            for item in data:
                dados.append({
                    'tipo_transacao': item.get('tipo_negocio', '').strip(),
                    'preco': Decimal(str(item.get('preco', 0))),
                    'quartos': int(item.get('quartos', 0)),
                    'bairro': item.get('bairro', '').strip(),
                    'endereco': item.get('endereco', '').strip(),
                    'descricao': item.get('descricao', '').strip(),
                })
        return dados

    def _salvar_imoveis(self, imoveis_data, origem_formato):
        objetos_imovel = []

        for item in imoveis_data:
            match = re.search(r'(?:codigo:|ref:\s*)([A-Z0-9-]+)', item['descricao'], re.IGNORECASE)
            ref_codigo = match.group(1) if match else 'SEM_REF'
            
            origem = f"carga_inicial_{origem_formato} | ref:{ref_codigo}"

            imovel = Imovel(
                tipo_transacao=item['tipo_transacao'],
                preco=item['preco'],
                quartos=item['quartos'],
                bairro=item['bairro'],
                endereco=item['endereco'],
                descricao=item['descricao'],
                origem_carga=origem
            )
            objetos_imovel.append(imovel)

        with transaction.atomic():
            Imovel.objects.bulk_create(objetos_imovel)

        self.stdout.write(
            self.style.SUCCESS(f"Sucesso! {len(objetos_imovel)} imóveis foram inseridos no banco de dados.")
        )


## Comando para docs:

# python manage.py importar_imoveis --filepath ../data/imoveis_resumo.json --format json
# python manage.py importar_imoveis --filepath ../data/imoveis.csv --format csv