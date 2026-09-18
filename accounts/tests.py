from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .models import Account, AccountBalanceAdjustment, FundTransfer
from .services import adjust_account_balance


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


class AccountBalanceAdjustmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reserve@example.com', password='test-password'
        )
        self.reserve = Account.objects.create(
            user=self.user,
            name='Cofre Mercado Pago',
            account_type='savings',
            balance=Decimal('100.00'),
        )

    def test_adjustment_records_old_new_and_delta(self):
        adjustment = AccountBalanceAdjustment.objects.create(
            user=self.user,
            account=self.reserve,
            previous_balance=Decimal('100.00'),
            new_balance=Decimal('125.50'),
            delta=Decimal('25.50'),
            adjustment_date=date.today(),
            reason='Rendimento do cofre',
            client_id='cofre-yield-001',
        )

        self.assertEqual(adjustment.delta, Decimal('25.50'))
        self.assertEqual(adjustment.account, self.reserve)

    def test_service_updates_reserve_and_reuses_same_client_id(self):
        first = adjust_account_balance(
            user=self.user,
            account_id=self.reserve.id,
            new_balance=Decimal('125.50'),
            adjustment_date=date.today(),
            reason='Rendimento do cofre',
            client_id='cofre-yield-service-001',
        )
        second = adjust_account_balance(
            user=self.user,
            account_id=self.reserve.id,
            new_balance=Decimal('125.50'),
            adjustment_date=date.today(),
            reason='Rendimento do cofre',
            client_id='cofre-yield-service-001',
        )

        self.reserve.refresh_from_db()
        self.assertEqual(self.reserve.balance, Decimal('125.50'))
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.previous_balance, Decimal('100.00'))

    def test_service_rejects_checking_account(self):
        checking = Account.objects.create(
            user=self.user, name='Operacional', account_type='checking'
        )

        with self.assertRaises(ValidationError):
            adjust_account_balance(
                user=self.user,
                account_id=checking.id,
                new_balance=Decimal('10.00'),
                adjustment_date=date.today(),
                reason='Não permitido',
                client_id='checking-adjustment-001',
            )
