"""
Forms for the profiles app.

Single source of truth: User model owns first_name/last_name. ProfileForm
edits both User and Profile fields atomically via a custom save().
"""

import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Profile

User = get_user_model()


# Allow letters (incl. accented), spaces, hyphen and apostrophe — common in
# real names like "Maria-Clara" or "D'Ávila".
_NAME_VALID_PATTERN = re.compile(r"^[A-Za-zÀ-ÿ' \-]+$")

# Avatar upload limits.
AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
AVATAR_MAX_DIMENSION = 4096  # px (per side)
AVATAR_ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def _normalize_phone_digits(value):
    """Return only digits from a phone string, or '' if value is empty."""
    if not value:
        return ''
    return re.sub(r'\D', '', value)


def _validate_avatar_file(uploaded):
    """
    Defensive validation for avatar uploads.

    Pillow `verify()` is the canonical way to confirm an upload really is an
    image of the claimed type, instead of trusting the filename extension or
    Content-Type header (both forgeable). After verify() the file pointer
    must be reset so Django can save it.
    """
    if uploaded.size > AVATAR_MAX_BYTES:
        raise ValidationError(
            f'Imagem muito grande (máx. {AVATAR_MAX_BYTES // (1024 * 1024)} MB).'
        )

    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        # Without Pillow we cannot validate — fail closed.
        raise ValidationError('Sistema sem suporte a imagens. Contate o administrador.')

    try:
        with Image.open(uploaded) as img:
            img.verify()
    except (UnidentifiedImageError, Exception):
        raise ValidationError('Arquivo enviado não é uma imagem válida.')
    finally:
        uploaded.seek(0)

    # Reopen to inspect format and size (verify() leaves img in unusable state)
    with Image.open(uploaded) as img:
        if img.format not in AVATAR_ALLOWED_FORMATS:
            raise ValidationError(
                f'Formato {img.format} não suportado. Use JPG, PNG ou WEBP.'
            )
        width, height = img.size
        if width > AVATAR_MAX_DIMENSION or height > AVATAR_MAX_DIMENSION:
            raise ValidationError(
                f'Imagem muito grande ({width}x{height}). '
                f'Máximo {AVATAR_MAX_DIMENSION}x{AVATAR_MAX_DIMENSION}.'
            )
    uploaded.seek(0)


class ProfileForm(forms.ModelForm):
    """
    Edit profile and user-name fields together.

    The User model owns first_name/last_name (Django's AbstractUser). We expose
    them as form-level fields here and persist them on User in `save()`.
    """

    first_name = forms.CharField(
        label='Primeiro Nome',
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Digite seu primeiro nome',
            'maxlength': 30,
        }),
    )
    last_name = forms.CharField(
        label='Sobrenome',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Digite seu sobrenome',
            'maxlength': 150,
        }),
    )
    avatar_clear = forms.BooleanField(
        label='Remover foto atual',
        required=False,
    )

    # Declared explicitly so the form accepts the masked input
    # ("(11) 98765-4321"), wider than the model's 11-char column.
    # `clean_phone` normalizes to digits before saving.
    phone = forms.CharField(
        label='Telefone',
        max_length=20,
        required=False,
        help_text='Digite com DDD. Aceita formato (11) 98765-4321.',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '(11) 98765-4321',
            'type': 'tel',
            'inputmode': 'numeric',
            'maxlength': 16,
            'data-mask': 'phone-br',
        }),
    )

    class Meta:
        model = Profile
        fields = ['avatar', 'phone', 'birth_date', 'bio']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'max': timezone.now().date().strftime('%Y-%m-%d'),
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Conte um pouco sobre você...',
                'rows': 4,
                'maxlength': 500,
            }),
        }
        labels = {
            'birth_date': 'Data de Nascimento',
            'bio': 'Biografia',
        }
        help_texts = {
            'birth_date': 'Sua data de nascimento (opcional).',
            'bio': 'Uma breve descrição sobre você (até 500 caracteres).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate name fields from the related User instance
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    @staticmethod
    def _clean_name(value, field_label):
        if not value:
            return value
        value = ' '.join(value.split())  # collapse spaces
        if not _NAME_VALID_PATTERN.match(value):
            raise ValidationError(
                f'{field_label} deve conter apenas letras, espaços, hífen ou apóstrofo.'
            )
        return value

    def clean_first_name(self):
        return self._clean_name(self.cleaned_data.get('first_name', ''), 'Primeiro nome')

    def clean_last_name(self):
        return self._clean_name(self.cleaned_data.get('last_name', ''), 'Sobrenome')

    def clean_phone(self):
        raw = self.cleaned_data.get('phone', '')
        digits = _normalize_phone_digits(raw)
        if not digits:
            return ''
        if len(digits) not in (10, 11):
            raise ValidationError(
                'Telefone inválido. Use DDD + número (10 ou 11 dígitos).'
            )
        return digits

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if not birth_date:
            return birth_date

        today = timezone.now().date()
        if birth_date > today:
            raise ValidationError('Data de nascimento não pode estar no futuro.')

        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        if age < 13:
            raise ValidationError('Você deve ter pelo menos 13 anos.')
        if age > 120:
            raise ValidationError('Verifique a data de nascimento.')
        return birth_date

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        # Only validate when a fresh upload is present. Existing FieldFile
        # values pass through untouched (avoids re-reading on every save).
        if avatar and hasattr(avatar, 'read'):
            _validate_avatar_file(avatar)
        return avatar

    def clean_bio(self):
        bio = self.cleaned_data.get('bio', '')
        if not bio:
            return bio
        bio = ' '.join(bio.split())
        if len(bio) < 10:
            raise ValidationError('A biografia deve ter pelo menos 10 caracteres.')
        return bio

    def save(self, commit=True):
        profile = super().save(commit=False)

        user = profile.user
        user.first_name = self.cleaned_data.get('first_name', '').title()
        user.last_name = self.cleaned_data.get('last_name', '').title()

        # Honour the explicit "remove avatar" checkbox. Calling .delete(save=False)
        # cleans the storage file; the actual DB row is updated on profile.save().
        if self.cleaned_data.get('avatar_clear') and profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None

        if commit:
            user.save(update_fields=['first_name', 'last_name'])
            profile.save()
        return profile
