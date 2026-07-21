import csv
import json
import re
from decimal import Decimal

from django.db import transaction

from iamoveis.models import Imovel


class ImportadorImoveisService:

    def importar(self, filepath, formato):
        formato = formato.lower()

        if formato == "csv":
            dados = self._parse_csv(filepath)

        elif formato == "json":
            dados = self._parse_json(filepath)

        else:
            raise ValueError(f"Formato '{formato}' não suportado.")

        return self._salvar_imoveis(dados, formato)

    def _parse_csv(self, filepath):
        dados = []

        with open(filepath, encoding="utf-8") as arquivo:

            reader = csv.DictReader(arquivo)

            for row in reader:

                dados.append({
                    "tipo_transacao": row.get("tipo_negocio", "").strip(),
                    "preco": Decimal(row.get("preco", 0)),
                    "quartos": int(row.get("quartos", 0)),
                    "bairro": row.get("bairro", "").strip(),
                    "endereco": row.get("endereco", "").strip(),
                    "descricao": row.get("descricao", "").strip(),
                })

        return dados

    def _parse_json(self, filepath):

        with open(filepath, encoding="utf-8") as arquivo:

            data = json.load(arquivo)

        dados = []

        for item in data:

            dados.append({
                "tipo_transacao": item.get("tipo_negocio", "").strip(),
                "preco": Decimal(str(item.get("preco", 0))),
                "quartos": int(item.get("quartos", 0)),
                "bairro": item.get("bairro", "").strip(),
                "endereco": item.get("endereco", "").strip(),
                "descricao": item.get("descricao", "").strip(),
            })

        return dados

    def _salvar_imoveis(self, dados, formato):

        objetos = []

        for item in dados:

            match = re.search(
                r"(?:codigo:|ref:\s*)([A-Z0-9-]+)",
                item["descricao"],
                re.IGNORECASE
            )

            referencia = match.group(1) if match else "SEM_REF"

            objetos.append(
                Imovel(
                    tipo_transacao=item["tipo_transacao"],
                    preco=item["preco"],
                    quartos=item["quartos"],
                    bairro=item["bairro"],
                    endereco=item["endereco"],
                    descricao=item["descricao"],
                    origem_carga=f"carga_inicial_{formato} | ref:{referencia}"
                )
            )

        with transaction.atomic():

            Imovel.objects.bulk_create(objetos)

        return len(objetos)
