"""
Test suite for the profiles app.

Coverage:
- Profile model helpers (phone_display, avatar_url, __str__)
- ProfileForm: name unification on User, phone normalization,
  hyphen/apostrophe in names, age boundaries, avatar validation
- Signals: auto Profile creation, avatar replacement cleanup, delete cleanup
- Views: legacy redirect, login required, user isolation
"""

import io
import os
import shutil
import tempfile
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import AVATAR_MAX_BYTES, ProfileForm
from .models import Profile

User = get_user_model()


def _png_bytes(width=200, height=200, color=(255, 0, 0)):
    """Render a small valid PNG in-memory for upload tests."""
    img = Image.new('RGB', (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _gif_bytes():
    """1x1 GIF87a (smallest valid GIF) — used to assert format rejection."""
    return (
        b'GIF87a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00,'
        b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    )


class ProfileTestMixin:
    """Helpers for setting up users."""

    @classmethod
    def make_user(cls, suffix='', **extra):
        defaults = dict(
            username=f'alice{suffix}',
            email=f'alice{suffix}@example.com',
            password='testpass123',
        )
        defaults.update(extra)
        return User.objects.create_user(**defaults)


class ProfileModelTests(ProfileTestMixin, TestCase):

    def setUp(self):
        self.user = self.make_user()
        # Profile is auto-created by signal
        self.profile = self.user.profile

    def test_str_uses_user_full_name_when_set(self):
        self.user.first_name = 'João'
        self.user.last_name = 'Silva'
        self.user.save()
        self.assertEqual(str(self.profile), 'João Silva')

    def test_str_falls_back_to_email(self):
        self.assertEqual(str(self.profile), f'Perfil de {self.user.email}')

    def test_phone_display_formats_11_digits(self):
        self.profile.phone = '11987654321'
        self.assertEqual(self.profile.phone_display, '(11) 98765-4321')

    def test_phone_display_formats_10_digits(self):
        self.profile.phone = '1133445566'
        self.assertEqual(self.profile.phone_display, '(11) 3344-5566')

    def test_phone_display_empty(self):
        self.assertEqual(self.profile.phone_display, '')

    def test_avatar_url_empty_when_no_upload(self):
        self.assertEqual(self.profile.avatar_url, '')


class ProfileFormNameTests(ProfileTestMixin, TestCase):

    def setUp(self):
        self.user = self.make_user()

    def _form(self, **data):
        base = {'first_name': '', 'last_name': '', 'phone': '', 'bio': ''}
        base.update(data)
        return ProfileForm(data=base, instance=self.user.profile)

    def test_first_and_last_name_persist_on_user(self):
        form = self._form(first_name='maria', last_name='silva')
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Maria')
        self.assertEqual(self.user.last_name, 'Silva')

    def test_hyphen_and_apostrophe_accepted_in_names(self):
        form = self._form(first_name='Maria-Clara', last_name="D'Ávila")
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Maria-Clara')
        self.assertEqual(self.user.last_name, "D'Ávila")

    def test_digits_rejected_in_names(self):
        form = self._form(first_name='João123')
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)


class ProfileFormPhoneTests(ProfileTestMixin, TestCase):

    def setUp(self):
        self.user = self.make_user()

    def _form(self, phone):
        return ProfileForm(
            data={'first_name': '', 'last_name': '', 'phone': phone, 'bio': ''},
            instance=self.user.profile,
        )

    def test_accepts_formatted_phone_and_stores_digits_only(self):
        form = self._form('(11) 98765-4321')
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '11987654321')

    def test_accepts_10_digit_landline(self):
        form = self._form('11 3344-5566')
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '1133445566')

    def test_rejects_short_phone(self):
        form = self._form('11999')
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_empty_phone_is_allowed(self):
        form = self._form('')
        self.assertTrue(form.is_valid(), form.errors)


class ProfileFormBirthDateTests(ProfileTestMixin, TestCase):

    def setUp(self):
        self.user = self.make_user()

    def _form(self, **data):
        base = {'first_name': '', 'last_name': '', 'phone': '', 'bio': ''}
        base.update(data)
        return ProfileForm(data=base, instance=self.user.profile)

    def test_future_birth_date_rejected(self):
        form = self._form(birth_date=(date.today().replace(year=date.today().year + 1)))
        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)

    def test_minimum_age_enforced(self):
        recent = date.today().replace(year=date.today().year - 5)
        form = self._form(birth_date=recent)
        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileFormAvatarTests(ProfileTestMixin, TestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = self.make_user()

    def _form(self, avatar_file=None, **data):
        base = {'first_name': '', 'last_name': '', 'phone': '', 'bio': ''}
        base.update(data)
        files = {'avatar': avatar_file} if avatar_file else None
        return ProfileForm(data=base, files=files, instance=self.user.profile)

    def test_valid_png_upload_accepted(self):
        upload = SimpleUploadedFile(
            'avatar.png', _png_bytes(), content_type='image/png',
        )
        form = self._form(avatar_file=upload)
        self.assertTrue(form.is_valid(), form.errors)
        profile = form.save()
        self.assertTrue(profile.avatar.name.startswith(f'avatars/{self.user.pk}/'))

    def test_oversized_upload_rejected(self):
        big_blob = b'\x00' * (AVATAR_MAX_BYTES + 1)
        upload = SimpleUploadedFile('big.png', big_blob, content_type='image/png')
        form = self._form(avatar_file=upload)
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_gif_format_rejected(self):
        upload = SimpleUploadedFile('a.gif', _gif_bytes(), content_type='image/gif')
        form = self._form(avatar_file=upload)
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_non_image_file_rejected(self):
        upload = SimpleUploadedFile(
            'pretend.png', b'this is not an image at all',
            content_type='image/png',
        )
        form = self._form(avatar_file=upload)
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_avatar_clear_removes_file(self):
        # First, attach an avatar
        upload = SimpleUploadedFile(
            'avatar.png', _png_bytes(), content_type='image/png',
        )
        ProfileForm(
            data={'first_name': '', 'last_name': '', 'phone': '', 'bio': ''},
            files={'avatar': upload},
            instance=self.user.profile,
        ).save()
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar)

        # Then clear it via the checkbox
        form = ProfileForm(
            data={
                'first_name': '', 'last_name': '', 'phone': '', 'bio': '',
                'avatar_clear': 'on',
            },
            instance=self.user.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileSignalTests(ProfileTestMixin, TestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_profile_created_for_new_user(self):
        user = self.make_user(suffix='-fresh')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_old_avatar_file_removed_on_replace(self):
        user = self.make_user()
        first = SimpleUploadedFile('a.png', _png_bytes(), content_type='image/png')
        user.profile.avatar.save('a.png', first, save=True)
        first_path = user.profile.avatar.path
        self.assertTrue(os.path.exists(first_path))

        second = SimpleUploadedFile('b.png', _png_bytes(color=(0, 255, 0)),
                                     content_type='image/png')
        user.profile.avatar.save('b.png', second, save=True)
        # Pre-save signal should have wiped the previous file from disk
        self.assertFalse(os.path.exists(first_path))

    def test_avatar_file_removed_on_profile_delete(self):
        user = self.make_user()
        upload = SimpleUploadedFile('a.png', _png_bytes(), content_type='image/png')
        user.profile.avatar.save('a.png', upload, save=True)
        path = user.profile.avatar.path
        self.assertTrue(os.path.exists(path))

        user.profile.delete()
        self.assertFalse(os.path.exists(path))


class ProfileViewTests(ProfileTestMixin, TestCase):

    def setUp(self):
        self.user = self.make_user()

    def test_legacy_users_profile_redirects_to_profiles_detail(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('users:profile'))
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp.url, reverse('profiles:detail'))

    def test_detail_view_requires_login(self):
        resp = self.client.get(reverse('profiles:detail'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.url)

    def test_edit_view_requires_login(self):
        resp = self.client.get(reverse('profiles:edit'))
        self.assertEqual(resp.status_code, 302)

    def test_user_only_sees_own_profile(self):
        other = self.make_user(suffix='2')
        other.first_name = 'Bob'
        other.save()
        self.client.force_login(self.user)
        resp = self.client.get(reverse('profiles:detail'))
        self.assertEqual(resp.status_code, 200)
        # The view scopes to request.user, so 'Bob' should never appear
        self.assertNotContains(resp, 'Bob')
