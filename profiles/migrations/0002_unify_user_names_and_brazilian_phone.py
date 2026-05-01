"""
Unify name fields on the User model and adopt Brazilian phone format.

Order matters:
1. Copy Profile.first_name / Profile.last_name into the linked User row.
2. Normalize Profile.phone to digits-only (so the new validator accepts it).
3. Remove the duplicated fields from Profile.
4. Alter the phone column to its tighter shape.
"""

import re

import django.core.validators
from django.db import migrations, models


def _digits_only(value):
    if not value:
        return ''
    return re.sub(r'\D', '', value)


def copy_names_to_user_and_normalize_phone(apps, schema_editor):
    Profile = apps.get_model('profiles', 'Profile')
    for profile in Profile.objects.select_related('user').all():
        user = profile.user
        # Only copy when the User field is empty — never clobber existing data.
        if profile.first_name and not user.first_name:
            user.first_name = profile.first_name
        if profile.last_name and not user.last_name:
            user.last_name = profile.last_name
        user.save(update_fields=['first_name', 'last_name'])

        # Strip formatting so the new regex (^\d{10,11}$) accepts existing rows.
        # Drop unrecoverable values rather than failing the migration.
        new_phone = _digits_only(profile.phone)
        if len(new_phone) not in (10, 11):
            new_phone = ''
        if new_phone != profile.phone:
            profile.phone = new_phone
            profile.save(update_fields=['phone'])


def reverse_noop(apps, schema_editor):
    """Reverse migration: data copy is irreversible by design.

    Going back means the duplicate fields are recreated empty by Django,
    which is acceptable for a rollback scenario. We do not attempt to
    restore the original phone formatting.
    """
    return


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            copy_names_to_user_and_normalize_phone,
            reverse_noop,
        ),
        migrations.RemoveField(
            model_name='profile',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='last_name',
        ),
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.CharField(
                blank=True,
                help_text='DDD + número (somente dígitos). Ex.: 11987654321',
                max_length=11,
                validators=[
                    django.core.validators.RegexValidator(
                        message='Telefone deve conter DDD + número (10 ou 11 dígitos).',
                        regex='^\\d{10,11}$',
                    )
                ],
                verbose_name='Telefone',
            ),
        ),
    ]
