from django.core.management.base import BaseCommand

from iamoveis.services.importar_imoveis import ImportadorImoveisService


class Command(BaseCommand):

    help = "Importa imóveis"

    def add_arguments(self, parser):

        parser.add_argument("--filepath", required=True)

        parser.add_argument(
            "--format",
            choices=["csv", "json"],
            required=True
        )

    def handle(self, *args, **options):

        service = ImportadorImoveisService()

        total = service.importar(
            filepath=options["filepath"],
            formato=options["format"]
        )

        self.stdout.write(
            self.style.SUCCESS(f"{total} imóveis importados.")
        )