import logging

from celery import shared_task
from django.conf import settings

from iamoveis.services.importar_imoveis import ImportadorImoveisService

logger = logging.getLogger(__name__)


@shared_task
def executar_carga_diaria_imoveis():

    logger.info("Iniciando carga")

    service = ImportadorImoveisService()

    total = service.importar(
        filepath=settings.IMOVEIS_JSON,
        formato="json"
    )

    logger.info("%s imóveis importados", total)