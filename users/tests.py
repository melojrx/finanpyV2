from datetime import date, timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import User


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(TestCase):
    def test_password_reset_email_uses_namespaced_confirm_url(self):
        User.objects.create_user(
            email='maria@example.com',
            password='old-password-123',
        )

        response = self.client.post(
            reverse('users:password_reset'),
            {'email': 'maria@example.com'},
        )

        self.assertRedirects(response, reverse('users:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/reset/', mail.outbox[0].body)


class DashboardPeriodFilterTests(TestCase):
    def setUp(self):
        from accounts.models import Account
        from categories.models import Category
        from transactions.models import Transaction

        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
        )
        self.client.login(email='test@example.com', password='testpass123')

        self.account = Account.objects.create(
            user=self.user,
            name='Conta Teste',
            account_type='checking',
            balance=Decimal('1000.00'),
        )
        self.category_income = Category.objects.create(
            user=self.user,
            name='Salário',
            category_type='INCOME',
        )
        self.category_expense = Category.objects.create(
            user=self.user,
            name='Alimentação',
            category_type='EXPENSE',
        )

        today = date.today()
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.category_income,
            transaction_type='INCOME',
            amount=Decimal('5000.00'),
            transaction_date=today,
            description='Salário',
            status='CONFIRMED',
        )
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.category_expense,
            transaction_type='EXPENSE',
            amount=Decimal('200.00'),
            transaction_date=today,
            description='Almoço',
            status='CONFIRMED',
        )
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.category_expense,
            transaction_type='EXPENSE',
            amount=Decimal('300.00'),
            transaction_date=today - timedelta(days=10),
            description='Compras semana passada',
            status='CONFIRMED',
        )

    def test_dashboard_default_period_is_month(self):
        response = self.client.get(reverse('users:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_period'], 'month')

    def test_dashboard_period_today(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'today'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_period'], 'today')
        self.assertIn('R$', response.context['monthly_income'])
        self.assertIn('5.000', response.context['monthly_income'])

    def test_dashboard_period_7d(self):
        response = self.client.get(reverse('users:dashboard'), {'period': '7d'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_period'], '7d')

    def test_dashboard_period_year(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'year'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_period'], 'year')

    def test_dashboard_invalid_period_falls_back_to_month(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_period'], 'month')

    def test_dashboard_today_excludes_old_transactions(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'today'})
        txs = list(response.context['recent_transactions'])
        for tx in txs:
            self.assertEqual(tx.transaction_date, date.today())

    def test_dashboard_period_choices_in_context(self):
        response = self.client.get(reverse('users:dashboard'))
        self.assertIn('period_choices', response.context)
        self.assertEqual(len(response.context['period_choices']), 4)

    def test_dashboard_period_label_in_context(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'year'})
        self.assertIn(str(date.today().year), response.context['period_label'])


class GetPeriodSummaryTests(TestCase):
    def setUp(self):
        from accounts.models import Account
        from categories.models import Category
        from transactions.models import Transaction

        self.user = User.objects.create_user(
            email='summary@example.com',
            password='testpass123',
        )
        self.account = Account.objects.create(
            user=self.user,
            name='Conta',
            account_type='checking',
            balance=Decimal('0'),
        )
        self.cat_income = Category.objects.create(
            user=self.user, name='Renda', category_type='INCOME',
        )
        self.cat_expense = Category.objects.create(
            user=self.user, name='Gasto', category_type='EXPENSE',
        )

        today = date.today()
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_income,
            transaction_type='INCOME', amount=Decimal('1000.00'),
            transaction_date=today, description='Income today', status='CONFIRMED',
        )
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('250.00'),
            transaction_date=today, description='Expense today', status='CONFIRMED',
        )
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('100.00'),
            transaction_date=today - timedelta(days=30),
            description='Old expense', status='CONFIRMED',
        )

    def test_period_summary_today(self):
        from transactions.models import Transaction
        today = date.today()
        result = Transaction.get_period_summary(self.user, today, today)
        self.assertEqual(result['income'], Decimal('1000.00'))
        self.assertEqual(result['expenses'], Decimal('250.00'))
        self.assertEqual(result['balance'], Decimal('750.00'))

    def test_period_summary_wide_range_includes_all(self):
        from transactions.models import Transaction
        today = date.today()
        start = today - timedelta(days=60)
        result = Transaction.get_period_summary(self.user, start, today)
        self.assertEqual(result['income'], Decimal('1000.00'))
        self.assertEqual(result['expenses'], Decimal('350.00'))
        self.assertEqual(result['balance'], Decimal('650.00'))

    def test_period_summary_excludes_pending(self):
        from transactions.models import Transaction
        today = date.today()
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_income,
            transaction_type='INCOME', amount=Decimal('9999.00'),
            transaction_date=today, description='Pending', status='PENDING',
        )
        result = Transaction.get_period_summary(self.user, today, today)
        self.assertEqual(result['income'], Decimal('1000.00'))


class DashboardNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='nav@example.com',
            password='testpass123',
        )
        self.client.login(email='nav@example.com', password='testpass123')

    def test_offset_negative_navigates_to_past(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'month', 'offset': '-1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_offset'], -1)
        self.assertTrue(response.context['can_go_next'])

    def test_offset_zero_is_current(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'month', 'offset': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_offset'], 0)
        self.assertFalse(response.context['can_go_next'])

    def test_positive_offset_clamped_to_zero(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'month', 'offset': '5'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_offset'], 0)

    def test_invalid_offset_defaults_to_zero(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'month', 'offset': 'abc'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_offset'], 0)

    def test_prev_next_offsets_in_context(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'month', 'offset': '-2'})
        self.assertEqual(response.context['prev_offset'], -3)
        self.assertEqual(response.context['next_offset'], -1)
        self.assertTrue(response.context['can_go_next'])

    def test_year_navigation(self):
        response = self.client.get(reverse('users:dashboard'), {'period': 'year', 'offset': '-1'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(date.today().year - 1), response.context['period_label'])
