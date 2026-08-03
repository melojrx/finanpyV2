from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Account, FundTransfer


User = get_user_model()


class FundTransferBalanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='transfer@example.com', password='test-password'
        )
        self.from_account = Account.objects.create(
            user=self.user,
            name='Origem',
            account_type='checking',
            balance=Decimal('100.00'),
        )
        self.to_account = Account.objects.create(
            user=self.user,
            name='Destino',
            account_type='checking',
            balance=Decimal('50.00'),
        )
        self.other_account = Account.objects.create(
            user=self.user,
            name='Outra conta',
            account_type='checking',
            balance=Decimal('20.00'),
        )

    def test_direct_orm_creation_updates_account_balances(self):
        FundTransfer.objects.create(
            user=self.user,
            from_account=self.from_account,
            to_account=self.to_account,
            amount=Decimal('30.00'),
            transfer_date=date.today(),
            description='Teste',
        )

        self.from_account.refresh_from_db()
        self.to_account.refresh_from_db()

        self.assertEqual(self.from_account.balance, Decimal('70.00'))
        self.assertEqual(self.to_account.balance, Decimal('80.00'))

    def test_deleting_transfer_reverts_account_balances(self):
        transfer = FundTransfer.objects.create(
            user=self.user,
            from_account=self.from_account,
            to_account=self.to_account,
            amount=Decimal('30.00'),
            transfer_date=date.today(),
            description='Teste',
        )

        transfer.delete()

        self.from_account.refresh_from_db()
        self.to_account.refresh_from_db()

        self.assertEqual(self.from_account.balance, Decimal('100.00'))
        self.assertEqual(self.to_account.balance, Decimal('50.00'))

    def test_cannot_change_transfer_financial_fields_after_creation(self):
        changes = (
            ('amount', Decimal('40.00')),
            ('from_account', self.other_account),
            ('to_account', self.other_account),
        )

        for field, value in changes:
            with self.subTest(field=field):
                transfer = FundTransfer.objects.create(
                    user=self.user,
                    from_account=self.from_account,
                    to_account=self.to_account,
                    amount=Decimal('30.00'),
                    transfer_date=date.today(),
                    description='Teste',
                )
                setattr(transfer, field, value)

                with self.assertRaises(ValidationError):
                    transfer.save()
