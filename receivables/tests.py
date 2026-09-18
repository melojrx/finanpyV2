from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Account
from .services import create_loan_receivable, settle_loan_receivable


User = get_user_model()


class LoanReceivableServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='loan@example.com', password='test-password'
        )
        self.account = Account.objects.create(
            user=self.user, name='Mercado Pago', account_type='checking',
            balance=Decimal('1000.00'),
        )

    def test_loan_debits_cash_and_settlement_credits_it_without_transaction(self):
        loan = create_loan_receivable(
            user=self.user, counterparty='Sabrina', amount=Decimal('600.00'),
            origin_account_id=self.account.id, loan_date=date.today(),
            description='Brabus Performance Store', expected_return_date=None,
            client_id='sabrina-001',
        )
        settlement = settle_loan_receivable(
            user=self.user, loan_id=loan.id, amount=Decimal('600.00'),
            target_account_id=self.account.id, settlement_date=date.today(),
            description='Devolução', client_id='sabrina-settle-001',
        )

        loan.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(loan.status, 'SETTLED')
        self.assertEqual(loan.outstanding_amount, Decimal('0.00'))
        self.assertEqual(settlement.amount, Decimal('600.00'))
        self.assertEqual(self.account.balance, Decimal('1000.00'))
