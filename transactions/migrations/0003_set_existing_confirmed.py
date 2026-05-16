from django.db import migrations
from django.utils import timezone


def set_existing_confirmed(apps, schema_editor):
    Transaction = apps.get_model('transactions', 'Transaction')
    Transaction.objects.filter(status='PENDING').update(
        status='CONFIRMED',
        confirmed_at=timezone.now(),
    )


def reverse_set_confirmed(apps, schema_editor):
    pass  # No safe reverse — data was already CONFIRMED semantically


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_transaction_auto_confirm_transaction_confirmed_at_and_more'),
    ]

    operations = [
        migrations.RunPython(set_existing_confirmed, reverse_set_confirmed),
    ]
