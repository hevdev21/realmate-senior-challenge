from celery import shared_task
from iamoveis.services.importar_imoveis import ImportadorImoveisService
from celery import group
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def executar_importacao_imoveis(filepath, formato):
    service = ImportadorImoveisService()
    return service.importar(filepath, formato)


@shared_task
def importar_json():
    service = ImportadorImoveisService()
    service.importar(settings.IMOVEIS_JSON, "json")


@shared_task
def importar_csv():
    service = ImportadorImoveisService()
    service.importar(settings.IMOVEIS_CSV, "csv")

@shared_task
def executar_carga_diaria():
    logger.info("Iniciando carga diária...")
    group(
        importar_json.s(),
        importar_csv.s(),
    ).apply_async()
    logger.info("Carga diária enviada para processamento.")