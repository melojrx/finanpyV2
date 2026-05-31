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
