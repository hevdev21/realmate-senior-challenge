import csv
import json
import re
from decimal import Decimal

from django.db import transaction

from iamoveis.models import Imovel


class ImportadorImoveisService:

    CAMPOS_ATUALIZAVEIS = ["preco", "quartos", "descricao", "origem_carga"]

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

    def _extrair_referencia(self, descricao):
        match = re.search(
            r"(?:codigo:|ref:\s*)([A-Z0-9-]+)",
            descricao,
            re.IGNORECASE
        )
        return match.group(1) if match else "SEM_REF"

    def _chave_dedup(self, item):

        return (item["endereco"], item["bairro"], item["tipo_transacao"])

    def _salvar_imoveis(self, dados, formato):
        processados = []
        for item in dados:
            referencia = self._extrair_referencia(item["descricao"])
            origem_carga = f"carga_inicial_{formato} | ref:{referencia}"
            chave = self._chave_dedup(item)
            processados.append((chave, item, origem_carga))

        chaves = [p[0] for p in processados]
        enderecos = [c[0] for c in chaves]
        bairros = [c[1] for c in chaves]

        existentes = Imovel.objects.filter(
            endereco__in=enderecos,
            bairro__in=bairros,
        )
        existentes_map = {
            (e.endereco, e.bairro, e.tipo_transacao): e
            for e in existentes
        }

        para_criar = {}  # chave -> Imovel (evita duplicar dentro do próprio arquivo)
        para_atualizar = {}  # chave -> Imovel

        for chave, item, origem_carga in processados:
            existente = existentes_map.get(chave) or para_atualizar.get(chave)

            if existente:
                existente.preco = item["preco"]
                existente.quartos = item["quartos"]
                existente.descricao = item["descricao"]
                existente.origem_carga = origem_carga
                para_atualizar[chave] = existente
                # se estava marcado pra criar (duplicata dentro do arquivo), remove
                para_criar.pop(chave, None)
            else:
                para_criar[chave] = Imovel(
                    tipo_transacao=item["tipo_transacao"],
                    preco=item["preco"],
                    quartos=item["quartos"],
                    bairro=item["bairro"],
                    endereco=item["endereco"],
                    descricao=item["descricao"],
                    origem_carga=origem_carga,
                )

        with transaction.atomic():
            if para_criar:
                Imovel.objects.bulk_create(list(para_criar.values()))

            if para_atualizar:
                Imovel.objects.bulk_update(
                    list(para_atualizar.values()),
                    self.CAMPOS_ATUALIZAVEIS,
                )

        return {
            "criados": len(para_criar),
            "atualizados": len(para_atualizar),
        }