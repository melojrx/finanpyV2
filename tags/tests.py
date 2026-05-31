from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

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
