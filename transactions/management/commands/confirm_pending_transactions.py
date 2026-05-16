from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from transactions.models import Transaction


class Command(BaseCommand):
    help = 'Efetiva transações pendentes com auto_confirm=True e transaction_date <= hoje'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria efetivado sem alterar dados',
        )

    def handle(self, *args, **options):
        today = date.today()
        dry_run = options['dry_run']

        pending = Transaction.objects.filter(
            status='PENDING',
            auto_confirm=True,
            transaction_date__lte=today,
        ).select_related('account', 'user')

        count = pending.count()

        if count == 0:
            self.stdout.write('Nenhuma transação pendente para efetivar.')
            return

        if dry_run:
            self.stdout.write(f'[DRY RUN] {count} transações seriam efetivadas:')
            for txn in pending:
                self.stdout.write(
                    f'  - {txn.id}: {txn.description} ({txn.amount})'
                    f' @ {txn.transaction_date}'
                )
            return

        confirmed = 0
        errors = 0
        for txn in pending:
            try:
                txn.status = 'CONFIRMED'
                txn.confirmed_at = timezone.now()
                txn.save()
                confirmed += 1
            except Exception as e:
                errors += 1
                self.stderr.write(f'Erro ao efetivar transação {txn.id}: {e}')

        self.stdout.write(
            self.style.SUCCESS(f'{confirmed} transação(ões) efetivada(s).')
        )
        if errors:
            self.stdout.write(
                self.style.ERROR(f'{errors} erro(s) durante efetivação.')
            )
