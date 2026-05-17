"""Testes da API DRF — foco em endpoints adicionados/refatorados no M5.

Cobre:
  - POST /api/v1/transactions/quick/ (action quick do TransactionViewSet)
    com defaults inteligentes, idempotência por client_id e ownership.
  - GET /api/v1/dashboard/snapshot/ (consolidado para PWA/Hermes).
  - GET /api/v1/sync/since/?ts= (delta para Service Worker).
  - POST /api/v1/transactions/from-receipt/ (share_target / OCR placeholder).
  - GET /handler/?q= (resolver de deeplinks web+finanpy://).
  - Campos enriquecidos do TransactionSerializer (amount_display,
    category_full_path, category_color, category_icon).

Auth: TokenAuthentication (default DRF do projeto). Os testes criam um Token
explicitamente em setUp.
"""

import io
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from accounts.models import Account
from categories.models import Category
from transactions.models import Transaction


User = get_user_model()


class APITestBase(APITestCase):
    """Base com user autenticado via Token + uma conta + 2 categorias."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='quickuser', email='quick@example.com', password='pw-secret-123'
        )
        cls.other = User.objects.create_user(
            username='otheruser', email='other@example.com', password='pw-secret-123'
        )
        cls.account = Account.objects.create(
            user=cls.user, name='Itau Corrente', account_type='checking',
            balance=Decimal('1000.00'), currency='BRL',
        )
        cls.cat_expense = Category.objects.create(
            user=cls.user, name='Mercado', category_type='EXPENSE',
            color='#EF4444', icon='🛍️',
        )
        cls.cat_income = Category.objects.create(
            user=cls.user, name='Salário', category_type='INCOME',
            color='#10B981', icon='👔',
        )
        cls.other_account = Account.objects.create(
            user=cls.other, name='Other Account', account_type='checking',
            balance=Decimal('0.00'), currency='BRL',
        )

    def setUp(self):
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
            HTTP_X_FORWARDED_PROTO='https',
        )


class QuickTransactionEndpointTests(APITestBase):
    url = '/api/v1/transactions/quick/'

    def test_creates_with_full_payload(self):
        payload = {
            'amount': '49.90',
            'transaction_type': 'EXPENSE',
            'account': self.account.pk,
            'category': self.cat_expense.pk,
            'description': 'Compra padaria',
            'transaction_date': '2026-05-10',
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        tx = Transaction.objects.get(pk=resp.data['id'])
        self.assertEqual(tx.user, self.user)
        self.assertEqual(tx.amount, Decimal('49.90'))
        self.assertEqual(tx.description, 'Compra padaria')
        self.assertEqual(str(tx.transaction_date), '2026-05-10')

        # Resposta enriquecida
        self.assertIn('amount_display', resp.data)
        self.assertIn('R$', resp.data['amount_display'])
        self.assertEqual(resp.data['category_color'], '#EF4444')
        self.assertEqual(resp.data['category_icon'], '🛍️')

    def test_defaults_description_to_category_name(self):
        payload = {
            'amount': '10.00',
            'transaction_type': 'EXPENSE',
            'account': self.account.pk,
            'category': self.cat_expense.pk,
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertEqual(resp.data['description'], 'Mercado')

    def test_defaults_transaction_date_to_today(self):
        payload = {
            'amount': '10.00',
            'transaction_type': 'EXPENSE',
            'account': self.account.pk,
            'category': self.cat_expense.pk,
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['transaction_date'], date.today().isoformat())

    def test_rejects_account_not_owned(self):
        payload = {
            'amount': '10.00',
            'transaction_type': 'EXPENSE',
            'account': self.other_account.pk,
            'category': self.cat_expense.pk,
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('account', resp.data)

    def test_idempotency_via_client_id_returns_existing(self):
        payload = {
            'amount': '25.00',
            'transaction_type': 'INCOME',
            'account': self.account.pk,
            'category': self.cat_income.pk,
            'client_id': 'pwa-uuid-abc-123',
        }
        first = self.client.post(self.url, payload, format='json')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.content)

        # Retransmissão (Background Sync) — mesmo client_id deve retornar 200 + mesmo id
        second = self.client.post(self.url, payload, format='json')
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.content)
        self.assertEqual(second.data['id'], first.data['id'])

        # Não duplicou
        self.assertEqual(
            Transaction.objects.filter(user=self.user, amount=Decimal('25.00')).count(),
            1,
        )

    def test_requires_authentication(self):
        anon = APIClient()
        anon.defaults['HTTP_X_FORWARDED_PROTO'] = 'https'
        resp = anon.post(self.url, {}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_validates_category_type_matches_transaction_type(self):
        # Categoria EXPENSE com transaction INCOME deve falhar (validação do model)
        payload = {
            'amount': '10.00',
            'transaction_type': 'INCOME',
            'account': self.account.pk,
            'category': self.cat_expense.pk,
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accepts_future_pending_transaction_without_balance_impact(self):
        future_date = date.today() + timedelta(days=10)
        payload = {
            'amount': '292.00',
            'transaction_type': 'EXPENSE',
            'account': self.account.pk,
            'category': self.cat_expense.pk,
            'description': 'Parcela Bianca futura',
            'transaction_date': future_date.isoformat(),
            'status': 'PENDING',
        }

        resp = self.client.post(self.url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        tx = Transaction.objects.get(pk=resp.data['id'])
        self.assertEqual(tx.status, 'PENDING')
        self.assertIsNone(tx.confirmed_at)
        self.assertEqual(resp.data['status'], 'PENDING')
        self.assertIn('status_display', resp.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))


class ManualPendingTransactionWorkflowTests(APITestBase):
    """Fluxo manual: criar previsão, relatar pendências e efetivar sob demanda."""

    transactions_url = '/api/v1/transactions/'

    def test_standard_post_defaults_to_confirmed_and_updates_balance(self):
        payload = {
            'amount': '49.90',
            'transaction_type': 'EXPENSE',
            'account': self.account.pk,
            'category': self.cat_expense.pk,
            'description': 'Mercado hoje',
            'transaction_date': date.today().isoformat(),
        }

        resp = self.client.post(self.transactions_url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        tx = Transaction.objects.get(pk=resp.data['id'])
        self.assertEqual(tx.status, 'CONFIRMED')
        self.assertIsNotNone(tx.confirmed_at)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('950.10'))

    def test_standard_post_can_create_future_pending_without_balance_impact(self):
        future_date = date.today() + timedelta(days=15)
        payload = {
            'amount': '1540.93',
            'transaction_type': 'INCOME',
            'account': self.account.pk,
            'category': self.cat_income.pk,
            'description': 'Aluguel futuro',
            'transaction_date': future_date.isoformat(),
            'status': 'PENDING',
        }

        resp = self.client.post(self.transactions_url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        tx = Transaction.objects.get(pk=resp.data['id'])
        self.assertEqual(tx.status, 'PENDING')
        self.assertIsNone(tx.confirmed_at)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

    def test_pending_report_returns_due_and_future_totals(self):
        due = Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('100.00'),
            description='Despesa vencida', transaction_date=date.today(),
            status='PENDING',
        )
        future = Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_income,
            transaction_type='INCOME', amount=Decimal('250.00'),
            description='Receita futura', transaction_date=date.today() + timedelta(days=5),
            status='PENDING',
        )
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('999.00'),
            description='Confirmada ignorada', transaction_date=date.today(),
            status='CONFIRMED', confirmed_at=timezone.now(),
        )

        resp = self.client.get(
            f'{self.transactions_url}pending/',
            {'until': (date.today() + timedelta(days=5)).isoformat()},
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data['summary']['count'], 2)
        self.assertEqual(Decimal(resp.data['summary']['income']), Decimal('250.00'))
        self.assertEqual(Decimal(resp.data['summary']['expenses']), Decimal('100.00'))
        self.assertEqual(Decimal(resp.data['summary']['net']), Decimal('150.00'))
        self.assertEqual({item['id'] for item in resp.data['results']}, {due.id, future.id})

    def test_due_pending_report_filters_until_today(self):
        due = Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('100.00'),
            description='Despesa vencida', transaction_date=date.today(),
            status='PENDING',
        )
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_income,
            transaction_type='INCOME', amount=Decimal('250.00'),
            description='Receita futura', transaction_date=date.today() + timedelta(days=5),
            status='PENDING',
        )

        resp = self.client.get(f'{self.transactions_url}pending/', {'due': 'true'})

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data['summary']['count'], 1)
        self.assertEqual(resp.data['results'][0]['id'], due.id)

    def test_confirm_action_confirms_pending_and_updates_balance(self):
        tx = Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('75.00'),
            description='Despesa a efetivar', transaction_date=date.today(),
            status='PENDING',
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

        resp = self.client.post(f'{self.transactions_url}{tx.id}/confirm/', {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'CONFIRMED')
        self.assertIsNotNone(tx.confirmed_at)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('925.00'))

    def test_confirm_action_rejects_non_pending_transaction(self):
        tx = Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('75.00'),
            description='Já confirmada', transaction_date=date.today(),
            status='CONFIRMED', confirmed_at=timezone.now(),
        )

        resp = self.client.post(f'{self.transactions_url}{tx.id}/confirm/', {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pendentes', resp.data['detail'])


class DashboardSnapshotTests(APITestBase):
    url = '/api/v1/dashboard/snapshot/'

    def test_empty_snapshot(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['totals']['transaction_count_month'], 0)
        self.assertEqual(resp.data['totals']['income_month'], '0.00')
        self.assertEqual(resp.data['recent_transactions'], [])

    def test_snapshot_with_data(self):
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_income,
            transaction_type='INCOME', amount=Decimal('500.00'),
            description='Freela', transaction_date=date.today(),
            status='CONFIRMED',
        )
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('120.00'),
            description='Conta de luz', transaction_date=date.today(),
            status='CONFIRMED',
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        totals = resp.data['totals']
        self.assertEqual(totals['transaction_count_month'], 2)
        self.assertEqual(Decimal(totals['income_month']), Decimal('500.00'))
        self.assertEqual(Decimal(totals['expenses_month']), Decimal('120.00'))
        self.assertEqual(Decimal(totals['balance_month']), Decimal('380.00'))
        self.assertEqual(len(resp.data['recent_transactions']), 2)

    def test_snapshot_isolates_users(self):
        Transaction.objects.create(
            user=self.other, account=self.other_account, category=Category.objects.create(
                user=self.other, name='X', category_type='INCOME',
            ),
            transaction_type='INCOME', amount=Decimal('999.99'),
            description='Other user', transaction_date=date.today(),
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.data['totals']['transaction_count_month'], 0)
        self.assertEqual(resp.data['recent_transactions'], [])

    def test_requires_authentication(self):
        anon = APIClient()
        anon.defaults['HTTP_X_FORWARDED_PROTO'] = 'https'
        resp = anon.get(self.url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_savings_pct_is_calculated(self):
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_income,
            transaction_type='INCOME', amount=Decimal('1000.00'),
            description='Salário', transaction_date=date.today(),
            status='CONFIRMED',
        )
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('250.00'),
            description='Mercado', transaction_date=date.today(),
            status='CONFIRMED',
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 750 saved / 1000 income = 75%
        self.assertEqual(resp.data['totals']['savings_pct'], 75)

    def test_include_budgets_returns_top_active_budgets(self):
        from budgets.models import Budget

        today = date.today()
        Budget.objects.create(
            user=self.user, category=self.cat_expense,
            name='Mercado mensal', planned_amount=Decimal('500.00'),
            start_date=today.replace(day=1),
            end_date=today.replace(day=28),
        )
        resp = self.client.get(self.url, {'include': 'budgets'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('budgets', resp.data)
        self.assertEqual(len(resp.data['budgets']), 1)
        b = resp.data['budgets'][0]
        self.assertEqual(b['name'], 'Mercado mensal')
        self.assertIn('percentage_used', b)
        self.assertIn('status', b)

    def test_include_goals_returns_active_goals(self):
        from goals.models import Goal

        Goal.objects.create(
            user=self.user, name='Viagem',
            target_amount=Decimal('5000.00'),
            current_amount=Decimal('1500.00'),
            icon='✈️', color='#10B981',
        )
        resp = self.client.get(self.url, {'include': 'goals'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('goals', resp.data)
        self.assertEqual(len(resp.data['goals']), 1)
        g = resp.data['goals'][0]
        self.assertEqual(g['name'], 'Viagem')
        # 1500/5000 = 30%
        self.assertEqual(g['progress_pct'], 30.0)

    def test_include_chart_6m_returns_six_months(self):
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_income,
            transaction_type='INCOME', amount=Decimal('300.00'),
            description='Receita', transaction_date=date.today(),
            status='CONFIRMED',
        )
        resp = self.client.get(self.url, {'include': 'chart_6m'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        chart = resp.data['chart_6m']
        self.assertEqual(len(chart['labels']), 6)
        self.assertEqual(len(chart['income']), 6)
        self.assertEqual(len(chart['expenses']), 6)
        # O último bucket (mês corrente) deve refletir a receita de 300
        self.assertEqual(chart['income'][-1], 300.0)

    def test_include_csv_combines_packages(self):
        resp = self.client.get(self.url, {'include': 'budgets,goals,chart_6m'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('budgets', resp.data)
        self.assertIn('goals', resp.data)
        self.assertIn('chart_6m', resp.data)

    def test_no_include_keeps_payload_lean(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Sem include, os pacotes opcionais não aparecem
        self.assertNotIn('budgets', resp.data)
        self.assertNotIn('goals', resp.data)
        self.assertNotIn('chart_6m', resp.data)


class TransactionSerializerEnrichedFieldsTests(APITestBase):
    """Garante que o serializer padrão expõe os campos novos para UI mobile."""

    def test_list_includes_amount_display_and_category_meta(self):
        Transaction.objects.create(
            user=self.user, account=self.account, category=self.cat_expense,
            transaction_type='EXPENSE', amount=Decimal('33.40'),
            description='Café', transaction_date=date.today(),
        )
        resp = self.client.get('/api/v1/transactions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results') or resp.data
        self.assertGreaterEqual(len(results), 1)
        first = results[0]
        self.assertIn('amount_display', first)
        self.assertIn('R$', first['amount_display'])
        self.assertEqual(first['category_color'], '#EF4444')
        self.assertEqual(first['category_icon'], '🛍️')
        # full_path deve existir mesmo sem hierarquia (== name)
        self.assertEqual(first['category_full_path'], 'Mercado')


class SyncSinceEndpointTests(APITestBase):
    """GET /api/v1/sync/since/?ts= — delta para reconciliação do SW."""

    url = '/api/v1/sync/since/'

    def test_requires_ts_param(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ts', resp.data['detail'].lower())

    def test_invalid_ts_returns_400(self):
        resp = self.client.get(self.url, {'ts': 'not-a-date'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_returns_only_records_after_ts(self):
        cutoff = timezone.now()

        # Garante que o INSERT abaixo cai depois do cutoff
        new_account = Account.objects.create(
            user=self.user, name='Nova conta', account_type='savings',
            balance=Decimal('100.00'), currency='BRL',
        )
        new_tx = Transaction.objects.create(
            user=self.user, account=new_account, category=self.cat_income,
            transaction_type='INCOME', amount=Decimal('50.00'),
            description='Pós-cutoff', transaction_date=date.today(),
        )

        ts = (cutoff - timedelta(seconds=1)).isoformat()
        resp = self.client.get(self.url, {'ts': ts})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        account_ids = [a['id'] for a in resp.data['accounts']]
        tx_ids = [t['id'] for t in resp.data['transactions']]
        self.assertIn(new_account.id, account_ids)
        self.assertIn(new_tx.id, tx_ids)

        # Garante metadados de resposta
        self.assertIn('server_time', resp.data)
        self.assertIn('since', resp.data)

    def test_isolates_per_user(self):
        ts = (timezone.now() - timedelta(days=30)).isoformat()
        # Cria registro do other user — não deve aparecer
        Transaction.objects.create(
            user=self.other, account=self.other_account,
            category=Category.objects.create(
                user=self.other, name='X', category_type='INCOME',
            ),
            transaction_type='INCOME', amount=Decimal('99.00'),
            description='Other', transaction_date=date.today(),
        )
        resp = self.client.get(self.url, {'ts': ts})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for tx in resp.data['transactions']:
            # Nenhuma tx do conjunto retornado deve ser da other_account
            self.assertNotIn(tx['account'], [self.other_account.id])

    def test_requires_authentication(self):
        anon = APIClient()
        anon.defaults['HTTP_X_FORWARDED_PROTO'] = 'https'
        resp = anon.get(self.url, {'ts': timezone.now().isoformat()})
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class ReceiptDraftEndpointTests(APITestBase):
    """POST /api/v1/transactions/from-receipt/ — share_target + OCR placeholder."""

    url = '/api/v1/transactions/from-receipt/'

    @staticmethod
    def _png_bytes():
        # PNG válido mínimo (1x1 pixel transparente)
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

    def test_accepts_image_via_share_target(self):
        upload = SimpleUploadedFile(
            'comprovante.png', self._png_bytes(), content_type='image/png'
        )
        resp = self.client.post(
            self.url,
            {'receipt': upload, 'title': 'Padaria Deisi', 'text': 'R$ 12,90'},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED, resp.content)
        self.assertEqual(resp.data['status'], 'draft')
        draft = resp.data['draft']
        # Hint do título deve virar descrição
        self.assertEqual(draft['description'], 'Padaria Deisi')
        # Conta default sugerida = a primeira ativa do usuário
        self.assertEqual(draft['account'], self.account.id)
        # Tipo default razoável
        self.assertEqual(draft['transaction_type'], 'EXPENSE')
        # Sem OCR ainda → confidence 0
        self.assertEqual(draft['confidence']['amount'], 0.0)
        self.assertEqual(resp.data['meta']['ocr_engine'], 'pending')

    def test_accepts_image_field_alias(self):
        # Nome alternativo "image" (em vez de "receipt") também deve funcionar
        upload = SimpleUploadedFile(
            'foto.png', self._png_bytes(), content_type='image/png'
        )
        resp = self.client.post(self.url, {'image': upload}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)

    def test_rejects_missing_file(self):
        resp = self.client.post(self.url, {'title': 'sem arquivo'}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_unsupported_mime(self):
        upload = SimpleUploadedFile(
            'malicioso.exe', b'MZ\x90\x00', content_type='application/x-msdownload'
        )
        resp = self.client.post(self.url, {'receipt': upload}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('accepted', resp.data)

    def test_requires_authentication(self):
        anon = APIClient()
        anon.defaults['HTTP_X_FORWARDED_PROTO'] = 'https'
        upload = SimpleUploadedFile('x.png', self._png_bytes(), content_type='image/png')
        resp = anon.post(self.url, {'receipt': upload}, format='multipart')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class DeeplinkHandlerTests(TestCase):
    def setUp(self):
        self.client.defaults['HTTP_X_FORWARDED_PROTO'] = 'https'

    """GET /handler/?q= — protocol_handlers do PWA.

    O handler é uma view do core (não da API), então não exige Token —
    é uma rota web simples que faz redirect 302.
    """

    url = '/handler/'

    def test_dashboard_deeplink(self):
        resp = self.client.get(self.url, {'q': 'web+finanpy://dashboard'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/dashboard/')

    def test_transaction_new_with_querystring(self):
        deeplink = (
            'web+finanpy://transaction/new?'
            'amount=35&description=uber&transaction_type=EXPENSE'
        )
        resp = self.client.get(self.url, {'q': deeplink})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/transactions/create/?'))
        self.assertIn('amount=35', resp.url)
        self.assertIn('description=uber', resp.url)
        self.assertIn('transaction_type=EXPENSE', resp.url)

    def test_transaction_new_filters_unsafe_querystring(self):
        # `redirect` não está na whitelist → não deve aparecer no destino
        deeplink = (
            'web+finanpy://transaction/new?amount=10&redirect=https://evil.com'
        )
        resp = self.client.get(self.url, {'q': deeplink})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('amount=10', resp.url)
        self.assertNotIn('evil.com', resp.url)
        self.assertNotIn('redirect=', resp.url)

    def test_transaction_detail_by_id(self):
        resp = self.client.get(self.url, {'q': 'web+finanpy://transaction/42'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/transactions/42/')

    def test_budget_deeplink(self):
        resp = self.client.get(self.url, {'q': 'web+finanpy://budget'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/budgets/plano/')

    def test_invalid_scheme_falls_back(self):
        resp = self.client.get(self.url, {'q': 'https://evil.com/'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/?deeplink_error='))

    def test_unknown_host_falls_back(self):
        resp = self.client.get(self.url, {'q': 'web+finanpy://xpto'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/?deeplink_error='))

    def test_missing_q_param(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/?deeplink_error='))
