from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator


def avatar_upload_path(instance, filename):
    """
    Store each user's avatar under media/avatars/<user_id>/<filename>.

    Keeping a per-user folder makes cleanup trivial when a user is deleted
    and prevents filename collisions across users.
    """
    return f'avatars/{instance.user_id}/{filename}'


class Profile(models.Model):
    """
    User profile model extending the base User model with additional personal information.
    
    This model maintains a one-to-one relationship with the User model to store
    extended profile information such as personal details, contact information,
    and biography. It follows the project's data isolation pattern by being
    directly linked to a user.
    
    Fields:
    - user: OneToOneField linking to the custom User model
    - first_name: User's first name (optional)
    - last_name: User's last name (optional)
    - phone: Phone number with validation (optional)
    - birth_date: Date of birth (optional)
    - bio: Short biography or description (optional)
    - created_at: Timestamp when profile was created
    - updated_at: Timestamp when profile was last updated
    """
    
    # Brazilian phone validator: stores only digits (10 or 11 — DDD + number).
    # International prefix is allowed at parse time but stripped before save.
    phone_validator = RegexValidator(
        regex=r'^\d{10,11}$',
        message='Telefone deve conter DDD + número (10 ou 11 dígitos).'
    )

    # One-to-one relationship with User model
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text='Associated user account for this profile'
    )

    # NOTE: first_name and last_name now live on the User model itself
    # (django.contrib.auth.AbstractUser provides them). Keeping them here
    # would force two-way syncing and was the root cause of the navbar
    # showing the email prefix instead of the user's name.

    phone = models.CharField(
        'Telefone',
        max_length=11,
        blank=True,
        validators=[phone_validator],
        help_text='DDD + número (somente dígitos). Ex.: 11987654321'
    )

    avatar = models.ImageField(
        'Foto de perfil',
        upload_to=avatar_upload_path,
        null=True,
        blank=True,
        help_text='Imagem JPG, PNG ou WEBP de até 2 MB.',
    )
    
    birth_date = models.DateField(
        'Birth Date',
        blank=True,
        null=True,
        help_text='User\'s date of birth'
    )
    
    bio = models.TextField(
        'Biography',
        max_length=500,
        blank=True,
        help_text='Short biography or description (max 500 characters)'
    )
    
    # Timestamp fields for audit trail
    created_at = models.DateTimeField(
        'Created At',
        auto_now_add=True,
        help_text='Timestamp when the profile was created'
    )
    
    updated_at = models.DateTimeField(
        'Updated At',
        auto_now=True,
        help_text='Timestamp when the profile was last updated'
    )
    
    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        db_table = 'profiles_profile'
        ordering = ['-created_at']  # Most recent first
        
    def __str__(self):
        """Return string representation of the profile."""
        # Avoid User.get_full_name(): the custom override falls back to email,
        # which would mask the empty-name case and break the email fallback here.
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        return full_name or f"Perfil de {self.user.email}"

    def clean(self):
        """
        Model-level validation.

        Validates that birth_date is not in the future.
        """
        from django.core.exceptions import ValidationError
        from django.utils import timezone

        super().clean()

        if self.birth_date and self.birth_date > timezone.now().date():
            raise ValidationError({
                'birth_date': 'A data de nascimento não pode estar no futuro.'
            })

    @property
    def phone_display(self):
        """Format the stored digits as `(XX) XXXXX-XXXX` or `(XX) XXXX-XXXX`."""
        digits = self.phone or ''
        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        if len(digits) == 10:
            return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
        return digits

    @property
    def avatar_url(self):
        """Return the avatar URL or empty string when no upload exists.

        Templates can use `{% if profile.avatar_url %}` to decide between the
        image and the initials fallback without raising ValueError when the
        FieldFile is empty.
        """
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return ''
    
    @property
    def age(self):
        """
        Calculate and return the user's age based on birth_date.
        Returns None if birth_date is not set.
        """
        if not self.birth_date:
            return None
            
        from django.utils import timezone
        today = timezone.now().date()
        age = today.year - self.birth_date.year
        
        # Adjust if birthday hasn't occurred this year
        if today.month < self.birth_date.month or (
            today.month == self.birth_date.month and today.day < self.birth_date.day
        ):
            age -= 1
            
        return age
