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
