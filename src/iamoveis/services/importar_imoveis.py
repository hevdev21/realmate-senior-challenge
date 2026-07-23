import csv
import json
import re
from decimal import Decimal
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from django.db import transaction

from iamoveis.models import Imovel

class ImovelDict(TypedDict):
    tipo_transacao: str
    preco: Decimal
    quartos: int
    bairro: str
    endereco: str
    descricao: str


@dataclass
class ResultadoImportacao:
    criados: int
    atualizados: int


ChaveDedup = tuple[str, str, str]

class ImportadorImoveisService:

    CAMPOS_ATUALIZAVEIS: list[str] = ["preco", "quartos", "descricao", "origem_carga"]

    def importar(self, filepath: str | Path, formato: str) -> ResultadoImportacao:
        formato = formato.lower()

        if formato == "csv":
            dados = self._parse_csv(filepath)

        elif formato == "json":
            dados = self._parse_json(filepath)

        else:
            raise ValueError(f"Formato '{formato}' não suportado.")

        return self._salvar_imoveis(dados, formato)

    def _parse_csv(self, filepath: str | Path) -> list[ImovelDict]:
        dados: list[ImovelDict] = []

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

    def _parse_json(self, filepath: str | Path) -> list[ImovelDict]:

        with open(filepath, encoding="utf-8") as arquivo:

            data = cast(list[dict[str, object]], json.load(arquivo))

        dados: list[ImovelDict] = []

        for item in data:
            quartos_raw = item.get("quartos", 0)
            quartos = int(quartos_raw) if isinstance(quartos_raw, (int, float, str)) else 0

            dados.append({
                "tipo_transacao": str(item.get("tipo_negocio") or "").strip(),
                "preco": Decimal(str(item.get("preco") or 0)),
                "quartos": quartos,
                "bairro": str(item.get("bairro") or "").strip(),
                "endereco": str(item.get("endereco") or "").strip(),
                "descricao": str(item.get("descricao") or "").strip(),
            })

        return dados

    def _extrair_referencia(self, descricao: str) -> str:
        match = re.search(
            r"(?:codigo:|ref:\s*)([A-Z0-9-]+)",
            descricao,
            re.IGNORECASE
        )
        return match.group(1) if match else "SEM_REF"

    def _chave_dedup(self, item: ImovelDict) -> ChaveDedup:

        return (item["endereco"], item["bairro"], item["tipo_transacao"])

    def _salvar_imoveis(self, dados: list[ImovelDict], formato: str) -> ResultadoImportacao:
        processados: list[tuple[ChaveDedup, ImovelDict, str]] = []

        for item in dados:
            referencia = self._extrair_referencia(item["descricao"])
            origem_carga = f"carga_inicial_{formato} | ref:{referencia}"
            chave = self._chave_dedup(item)
            processados.append((chave, item, origem_carga))

        enderecos = [c[0][0] for c in processados]
        bairros = [c[0][1] for c in processados]

        existentes = Imovel.objects.filter(endereco__in=enderecos, bairro__in=bairros)
        existentes_map: dict[ChaveDedup, Imovel] = {
            (e.endereco or "", e.bairro or "", e.tipo_transacao or ""): e
            for e in existentes
        }

        para_criar: dict[ChaveDedup, Imovel] = {}
        para_atualizar: dict[ChaveDedup, Imovel] = {}

        for chave, item, origem_carga in processados:
            existente = existentes_map.get(chave) or para_atualizar.get(chave)

            if existente:
                existente.preco = item["preco"]
                existente.quartos = item["quartos"]
                existente.descricao = item["descricao"]
                existente.origem_carga = origem_carga
                para_atualizar[chave] = existente
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

        return ResultadoImportacao(
            criados=len(para_criar),
            atualizados=len(para_atualizar),
        )