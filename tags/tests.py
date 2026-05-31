from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse

from .models import Tag

User = get_user_model()


class TagModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com', password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='otheruser@example.com', password='testpass123'
        )

    def test_create_tag(self):
        tag = Tag.objects.create(user=self.user, name='viagem')
        self.assertEqual(tag.name, 'viagem')
        self.assertEqual(tag.user, self.user)
        self.assertIsNotNone(tag.created_at)

    def test_name_normalized_lowercase(self):
        tag = Tag.objects.create(user=self.user, name='  Viagem  ')
        self.assertEqual(tag.name, 'viagem')

    def test_unique_per_user(self):
        Tag.objects.create(user=self.user, name='viagem')
        with self.assertRaises((ValidationError, IntegrityError)):
            Tag.objects.create(user=self.user, name='viagem')

    def test_same_name_different_users(self):
        Tag.objects.create(user=self.user, name='viagem')
        tag2 = Tag.objects.create(user=self.other_user, name='viagem')
        self.assertEqual(tag2.name, 'viagem')

    def test_empty_name_raises(self):
        with self.assertRaises(ValidationError):
            Tag.objects.create(user=self.user, name='')

    def test_whitespace_only_name_raises(self):
        with self.assertRaises(ValidationError):
            Tag.objects.create(user=self.user, name='   ')

    def test_str(self):
        tag = Tag.objects.create(user=self.user, name='reembolso')
        self.assertEqual(str(tag), 'reembolso')

    def test_ordering(self):
        Tag.objects.create(user=self.user, name='zoo')
        Tag.objects.create(user=self.user, name='alfa')
        tags = list(Tag.objects.filter(user=self.user).values_list('name', flat=True))
        self.assertEqual(tags, ['alfa', 'zoo'])


class TagViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='viewuser@test.com', password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='otherviewuser@test.com', password='testpass123'
        )
        self.client.login(email='viewuser@test.com', password='testpass123')
        self.tag = Tag.objects.create(user=self.user, name='viagem')

    def test_list_view(self):
        response = self.client.get(reverse('tags:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'viagem')

    def test_list_view_user_isolation(self):
        Tag.objects.create(user=self.other_user, name='secreto')
        response = self.client.get(reverse('tags:list'))
        self.assertNotContains(response, 'secreto')

    def test_create_view(self):
        response = self.client.post(
            reverse('tags:create'), {'name': 'reembolso'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tag.objects.filter(user=self.user, name='reembolso').exists())

    def test_create_duplicate_fails(self):
        response = self.client.post(
            reverse('tags:create'), {'name': 'viagem'}
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view(self):
        response = self.client.post(
            reverse('tags:update', kwargs={'pk': self.tag.pk}),
            {'name': 'trabalho'},
        )
        self.assertEqual(response.status_code, 302)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, 'trabalho')

    def test_update_other_user_tag_404(self):
        other_tag = Tag.objects.create(user=self.other_user, name='alheia')
        response = self.client.post(
            reverse('tags:update', kwargs={'pk': other_tag.pk}),
            {'name': 'hack'},
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_view(self):
        response = self.client.post(
            reverse('tags:delete', kwargs={'pk': self.tag.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Tag.objects.filter(pk=self.tag.pk).exists())

    def test_delete_other_user_tag_404(self):
        other_tag = Tag.objects.create(user=self.other_user, name='alheia')
        response = self.client.post(
            reverse('tags:delete', kwargs={'pk': other_tag.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(reverse('tags:list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


from rest_framework.test import APITestCase, APIClient
from rest_framework import status as http_status
from transactions.models import Transaction
from accounts.models import Account
from categories.models import Category
from datetime import date


class TagAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='apiuser@test.com', password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='otherapiuser@test.com', password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.tag = Tag.objects.create(user=self.user, name='viagem')

    def _get_results(self, response):
        """Handle both paginated and non-paginated responses."""
        if isinstance(response.data, dict) and 'results' in response.data:
            return response.data['results']
        return response.data

    def test_list_tags(self):
        response = self.client.get('/api/v1/tags/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        results = self._get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'viagem')

    def test_list_tags_user_isolation(self):
        Tag.objects.create(user=self.other_user, name='secreto')
        response = self.client.get('/api/v1/tags/')
        results = self._get_results(response)
        self.assertEqual(len(results), 1)

    def test_create_tag(self):
        response = self.client.post('/api/v1/tags/', {'name': 'reembolso'})
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'reembolso')
        self.assertTrue(Tag.objects.filter(user=self.user, name='reembolso').exists())

    def test_create_duplicate_tag(self):
        response = self.client.post('/api/v1/tags/', {'name': 'viagem'})
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_update_tag(self):
        response = self.client.patch(
            f'/api/v1/tags/{self.tag.pk}/', {'name': 'trabalho'}
        )
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, 'trabalho')

    def test_delete_tag(self):
        response = self.client.delete(f'/api/v1/tags/{self.tag.pk}/')
        self.assertEqual(response.status_code, http_status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(pk=self.tag.pk).exists())

    def test_cannot_access_other_user_tag(self):
        other_tag = Tag.objects.create(user=self.other_user, name='alheia')
        response = self.client.get(f'/api/v1/tags/{other_tag.pk}/')
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)


class TransactionTagAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='txtaguser@test.com', password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.account = Account.objects.create(
            user=self.user, name='Conta Test',
            account_type='checking', balance=1000, currency='BRL',
        )
        self.category = Category.objects.create(
            user=self.user, name='Alimentação',
            category_type='EXPENSE',
        )
        self.tag1 = Tag.objects.create(user=self.user, name='viagem')
        self.tag2 = Tag.objects.create(user=self.user, name='trabalho')

    def test_create_transaction_with_tags(self):
        data = {
            'transaction_type': 'EXPENSE',
            'amount': '50.00',
            'description': 'Almoço viagem',
            'transaction_date': '2026-05-31',
            'account': self.account.pk,
            'category': self.category.pk,
            'status': 'CONFIRMED',
            'tag_ids': [self.tag1.pk, self.tag2.pk],
        }
        response = self.client.post('/api/v1/transactions/', data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['tags']), 2)

    def test_filter_transactions_by_tag(self):
        tx = Transaction(
            user=self.user, account=self.account, category=self.category,
            transaction_type='EXPENSE', amount=30,
            description='Com tag', transaction_date=date.today(),
            status='CONFIRMED',
        )
        tx.save()
        tx.tags.add(self.tag1)

        tx2 = Transaction(
            user=self.user, account=self.account, category=self.category,
            transaction_type='EXPENSE', amount=20,
            description='Sem tag', transaction_date=date.today(),
            status='CONFIRMED',
        )
        tx2.save()

        response = self.client.get('/api/v1/transactions/?tag=viagem')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        results = self._get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['description'], 'Com tag')

    def _get_results(self, response):
        if isinstance(response.data, dict) and 'results' in response.data:
            return response.data['results']
        return response.data


class TagTransactionIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='integuser@test.com', password='testpass123'
        )
        self.client.login(email='integuser@test.com', password='testpass123')

        self.account = Account.objects.create(
            user=self.user, name='Conta Integração',
            account_type='checking', balance=5000, currency='BRL',
        )
        self.category = Category.objects.create(
            user=self.user, name='Transporte',
            category_type='EXPENSE',
        )
        self.tag = Tag.objects.create(user=self.user, name='viagem')

    def test_create_transaction_with_existing_tag(self):
        data = {
            'transaction_type': 'EXPENSE',
            'amount': '100.00',
            'description': 'Uber aeroporto',
            'transaction_date': '2026-05-31',
            'account': self.account.pk,
            'category': self.category.pk,
            'status': 'CONFIRMED',
            'tags': [self.tag.pk],
        }
        response = self.client.post(reverse('transactions:create'), data)
        self.assertEqual(response.status_code, 302)

        tx = Transaction.objects.get(description='Uber aeroporto')
        self.assertIn(self.tag, tx.tags.all())

    def test_filter_transactions_by_tag_in_list(self):
        tx1 = Transaction(
            user=self.user, account=self.account, category=self.category,
            transaction_type='EXPENSE', amount=50,
            description='Com tag', transaction_date=date.today(),
            status='CONFIRMED',
        )
        tx1.save()
        tx1.tags.add(self.tag)

        tx2 = Transaction(
            user=self.user, account=self.account, category=self.category,
            transaction_type='EXPENSE', amount=30,
            description='Sem tag', transaction_date=date.today(),
            status='CONFIRMED',
        )
        tx2.save()

        response = self.client.get(
            reverse('transactions:list') + f'?tags={self.tag.pk}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Com tag')
        self.assertNotContains(response, 'Sem tag')

    def test_transaction_detail_shows_tags(self):
        tx = Transaction(
            user=self.user, account=self.account, category=self.category,
            transaction_type='EXPENSE', amount=75,
            description='Almoço trabalho', transaction_date=date.today(),
            status='CONFIRMED',
        )
        tx.save()
        tx.tags.add(self.tag)

        response = self.client.get(
            reverse('transactions:detail', kwargs={'pk': tx.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'viagem')
