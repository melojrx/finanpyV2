# Transaction Status (FIN-14) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add status field (PENDING/CONFIRMED/CANCELLED) to Transaction model so users can plan future transactions and control when they impact account balance.

**Architecture:** Add `status`, `auto_confirm`, `confirmed_at` fields to existing Transaction model. Refactor signals to only affect balance for CONFIRMED transactions. Add confirm/cancel views and management command for auto-confirmation.

**Tech Stack:** Django 5.2+, Python 3.13+, SQLite (dev), PostgreSQL (prod)

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `transactions/models.py` | Add status fields, update validation |
| Modify | `transactions/signals.py` | Status-aware balance logic |
| Modify | `transactions/forms.py` | Add status/auto_confirm to forms |
| Modify | `transactions/views.py` | Add confirm/cancel/bulk views |
| Modify | `transactions/urls.py` | New URL patterns |
| Modify | `transactions/tests.py` | Update existing + add status tests |
| Create | `transactions/management/__init__.py` | Package init |
| Create | `transactions/management/commands/__init__.py` | Package init |
| Create | `transactions/management/commands/confirm_pending_transactions.py` | Auto-confirm command |
| Modify | `templates/transactions/transaction_list.html` | Status badges, filter tabs, action buttons |
| Modify | `templates/transactions/transaction_form.html` | Status field in form |
| Modify | `templates/transactions/transaction_detail.html` | Status display + actions |

---

### Task 1: Model — Add status fields

**Files:**
- Modify: `transactions/models.py`

- [ ] **Step 1: Add STATUS_CHOICES and new fields to Transaction model**

In `transactions/models.py`, add after `RECURRENCE_TYPE_CHOICES`:

```python
STATUS_CHOICES = [
    ('PENDING', 'Pendente'),
    ('CONFIRMED', 'Efetivada'),
    ('CANCELLED', 'Cancelada'),
]
```

Add these fields after `recurrence_type`:

```python
status = models.CharField(
    max_length=10,
    choices=STATUS_CHOICES,
    default='PENDING',
    verbose_name='Status',
    help_text='Status da transação: pendente, efetivada ou cancelada',
)

auto_confirm = models.BooleanField(
    default=False,
    verbose_name='Efetivar automaticamente',
    help_text='Se True, efetiva automaticamente na data via cron',
)

confirmed_at = models.DateTimeField(
    null=True,
    blank=True,
    verbose_name='Efetivada em',
    help_text='Timestamp de quando a transação foi efetivada',
)
```

- [ ] **Step 2: Add indexes for status queries**

In `class Meta`, add to the `indexes` list:

```python
models.Index(fields=['user', 'status']),
models.Index(fields=['status', 'transaction_date', 'auto_confirm']),
```

- [ ] **Step 3: Remove future date validation from clean()**

In the `clean()` method, remove this block (lines 179-182):

```python
# Validate transaction date is not in the future
if self.transaction_date and self.transaction_date > date.today():
    raise ValidationError({
        'transaction_date': 'Transaction date cannot be in the future.'
    })
```

- [ ] **Step 4: Add status transition validation to clean()**

Add at the end of `clean()`, before the recurring transaction validation:

```python
# Validate status transitions
if self.pk:
    try:
        old = Transaction.objects.only('status').get(pk=self.pk)
        valid_transitions = {
            'PENDING': ('CONFIRMED', 'CANCELLED'),
            'CONFIRMED': ('CANCELLED',),
            'CANCELLED': (),
        }
        if self.status != old.status:
            allowed = valid_transitions.get(old.status, ())
            if self.status not in allowed:
                raise ValidationError({
                    'status': f'Transição de {old.get_status_display()} para '
                              f'{self.get_status_display()} não é permitida.'
                })
    except Transaction.DoesNotExist:
        pass

# Validate auto_confirm only makes sense for PENDING
if self.auto_confirm and self.status != 'PENDING':
    raise ValidationError({
        'auto_confirm': 'Efetivação automática só se aplica a transações pendentes.'
    })
```

- [ ] **Step 5: Update get_monthly_summary to filter by CONFIRMED**

In `get_monthly_summary` classmethod, change the base queryset:

```python
transactions = cls.objects.filter(
    user=user,
    transaction_date__year=year,
    transaction_date__month=month,
    status='CONFIRMED',
)
```

- [ ] **Step 6: Add helper properties**

Add after existing properties:

```python
@property
def is_pending(self):
    return self.status == 'PENDING'

@property
def is_confirmed(self):
    return self.status == 'CONFIRMED'

@property
def is_cancelled(self):
    return self.status == 'CANCELLED'

@property
def status_color(self):
    colors = {
        'PENDING': 'text-yellow-400',
        'CONFIRMED': 'text-green-400',
        'CANCELLED': 'text-gray-400',
    }
    return colors.get(self.status, 'text-gray-400')

@property
def status_badge_classes(self):
    classes = {
        'PENDING': 'bg-yellow-900/40 text-yellow-300 border-yellow-700/50',
        'CONFIRMED': 'bg-green-900/40 text-green-300 border-green-700/50',
        'CANCELLED': 'bg-gray-900/40 text-gray-400 border-gray-700/50',
    }
    return classes.get(self.status, '')
```

- [ ] **Step 7: Run makemigrations and verify**

Run: `python manage.py makemigrations transactions`
Expected: Migration file created with AddField for status, auto_confirm, confirmed_at + AddIndex

- [ ] **Step 8: Commit**

```bash
git add transactions/models.py transactions/migrations/
git commit -m "feat(transactions): add status, auto_confirm, confirmed_at fields

Part of FIN-14. Adds PENDING/CONFIRMED/CANCELLED status to Transaction
model with transition validation and removes future date restriction."
```

---

### Task 2: Data Migration — Set existing transactions as CONFIRMED

**Files:**
- Create: `transactions/migrations/0003_set_existing_confirmed.py` (number may vary)

- [ ] **Step 1: Create data migration**

Run: `python manage.py makemigrations transactions --empty -n set_existing_confirmed`

- [ ] **Step 2: Write migration code**

Edit the generated migration file:

```python
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
```

Note: Adjust the dependency name to match the actual migration filename from Task 1 Step 7.

- [ ] **Step 3: Run migrate and verify**

Run: `python manage.py migrate transactions`
Expected: Both migrations applied successfully.

Run: `python manage.py shell -c "from transactions.models import Transaction; print(Transaction.objects.filter(status='PENDING').count())"`
Expected: `0`

- [ ] **Step 4: Commit**

```bash
git add transactions/migrations/
git commit -m "data(transactions): migrate existing transactions to CONFIRMED status"
```

---

### Task 3: Signals — Status-aware balance updates

**Files:**
- Modify: `transactions/signals.py`

- [ ] **Step 1: Update handle_transaction_pre_save to store old status**

In `handle_transaction_pre_save`, update the stored values dict to include status:

```python
_old_transaction_values[instance.pk] = {
    'account_id': old_transaction.account_id,
    'amount': old_transaction.amount,
    'transaction_type': old_transaction.transaction_type,
    'status': old_transaction.status,
}
```

- [ ] **Step 2: Rewrite handle_transaction_save for status awareness**

Replace the entire `handle_transaction_save` function:

```python
@receiver(post_save, sender='transactions.Transaction')
def handle_transaction_save(sender, instance, created, **kwargs):
    """
    Signal handler for transaction creation and updates.
    Only CONFIRMED transactions affect account balance.
    """
    try:
        if created:
            if instance.status != 'CONFIRMED':
                logger.info(f"Transaction {instance.id} created as {instance.status}, no balance impact")
                return

            logger.info(f"Processing new CONFIRMED transaction {instance.id}: {instance}")

            try:
                if not instance.user or not instance.account:
                    logger.error(f"Transaction {instance.id} missing user or account")
                    return
                if instance.account.user != instance.user:
                    logger.error(f"User mismatch for transaction {instance.id}")
                    return
            except Exception as e:
                logger.error(f"Error validating relationships for transaction {instance.id}: {e}")
                return

            delta = calculate_balance_delta(instance)
            update_account_balance(instance.account, delta, 'add')

        else:
            logger.info(f"Processing transaction update {instance.id}")

            old_values = _old_transaction_values.pop(instance.pk, None)
            if not old_values:
                logger.warning(f"No old values for transaction {instance.id}, skipping")
                return

            old_status = old_values.get('status', 'CONFIRMED')
            new_status = instance.status

            try:
                # Case 1: Status changed
                if old_status != new_status:
                    if old_status == 'PENDING' and new_status == 'CONFIRMED':
                        # Newly confirmed — apply delta
                        delta = calculate_balance_delta(instance)
                        update_account_balance(instance.account, delta, 'add')
                        logger.info(f"Transaction {instance.id} confirmed, balance updated")

                    elif old_status == 'CONFIRMED' and new_status == 'CANCELLED':
                        # Cancelled confirmed — reverse delta
                        class MockOld:
                            def __init__(self, v):
                                self.amount = v['amount']
                                self.transaction_type = v['transaction_type']
                        old_delta = calculate_balance_delta(MockOld(old_values))
                        from accounts.models import Account
                        old_account = Account.objects.get(pk=old_values['account_id'])
                        update_account_balance(old_account, old_delta, 'subtract')
                        logger.info(f"Transaction {instance.id} cancelled, balance reversed")

                    # PENDING → CANCELLED: no balance impact
                    # Any other transition: no balance impact

                # Case 2: Still CONFIRMED but amount/type/account changed
                elif new_status == 'CONFIRMED':
                    if (instance.amount != old_values['amount'] or
                        instance.transaction_type != old_values['transaction_type'] or
                        instance.account_id != old_values['account_id']):

                        class MockOld:
                            def __init__(self, v):
                                self.account_id = v['account_id']
                                self.amount = v['amount']
                                self.transaction_type = v['transaction_type']

                        old_tx = MockOld(old_values)

                        if instance.account_id != old_values['account_id']:
                            # Account changed — reverse on old, apply on new
                            old_delta = calculate_balance_delta(old_tx)
                            from accounts.models import Account
                            old_account = Account.objects.get(pk=old_values['account_id'])
                            update_account_balance(old_account, old_delta, 'subtract')
                            new_delta = calculate_balance_delta(instance)
                            update_account_balance(instance.account, new_delta, 'add')
                        else:
                            # Same account, amount or type changed
                            old_delta = calculate_balance_delta(old_tx)
                            update_account_balance(instance.account, old_delta, 'subtract')
                            new_delta = calculate_balance_delta(instance)
                            update_account_balance(instance.account, new_delta, 'add')

                # Case 3: Still PENDING or CANCELLED — no balance impact

            except Exception as e:
                logger.error(f"Error handling transaction update {instance.id}: {e}")

    except Exception as e:
        logger.error(f"Error in transaction save signal for {instance.id}: {e}")
```

- [ ] **Step 3: Update handle_transaction_delete for status awareness**

Replace the `handle_transaction_delete` function:

```python
@receiver(post_delete, sender='transactions.Transaction')
def handle_transaction_delete(sender, instance, **kwargs):
    """
    Signal handler for transaction deletion.
    Only reverses balance for CONFIRMED transactions.
    """
    try:
        if instance.status != 'CONFIRMED':
            logger.info(f"Transaction {instance.id} deleted (status={instance.status}), no balance impact")
            return

        logger.info(f"Processing CONFIRMED transaction deletion {instance.id}")

        if not instance.account:
            logger.warning(f"Transaction {instance.id} has no account reference")
            return

        if instance.account.user != instance.user:
            logger.error(f"User mismatch on deletion for transaction {instance.id}")
            return

        delta = calculate_balance_delta(instance)
        update_account_balance(instance.account, delta, 'subtract')

    except Exception as e:
        logger.error(f"Error in transaction delete signal for {instance.id}: {e}")
```

- [ ] **Step 4: Update recalculate_account_balance to filter CONFIRMED only**

In `recalculate_account_balance`, change:

```python
balance_impact = account.transactions.filter(status='CONFIRMED').aggregate(
```

- [ ] **Step 5: Commit**

```bash
git add transactions/signals.py
git commit -m "refactor(signals): only update balance for CONFIRMED transactions

Handles all status transitions: PENDING→CONFIRMED applies delta,
CONFIRMED→CANCELLED reverses delta, edits to CONFIRMED recalculate."
```

---

### Task 4: Forms — Add status and auto_confirm fields

**Files:**
- Modify: `transactions/forms.py`

- [ ] **Step 1: Update TransactionForm Meta.fields and widgets**

In `TransactionForm.Meta`, update `fields`:

```python
fields = [
    'transaction_type', 'account', 'category', 'amount',
    'description', 'transaction_date', 'status', 'auto_confirm', 'notes'
]
```

Add to `widgets`:

```python
'status': forms.Select(attrs={
    'class': 'form-select',
    'id': 'id_status',
    'aria-label': 'Status da transação',
}),
'auto_confirm': forms.CheckboxInput(attrs={
    'class': 'form-checkbox h-5 w-5 text-sky-500 rounded border-gray-600 bg-gray-700',
    'id': 'id_auto_confirm',
    'aria-label': 'Efetivar automaticamente na data',
}),
```

- [ ] **Step 2: Remove future date restriction from transaction_date widget**

In the `widgets` dict, change `transaction_date`:

```python
'transaction_date': forms.DateInput(attrs={
    'class': 'form-input',
    'type': 'date',
    'aria-label': 'Data da transação',
}),
```

(Remove the `'max': date.today().isoformat()` line)

- [ ] **Step 3: Update clean_transaction_date to allow future dates**

Replace `clean_transaction_date`:

```python
def clean_transaction_date(self):
    """Clean and validate transaction date."""
    transaction_date = self.cleaned_data.get('transaction_date')

    if not transaction_date:
        raise ValidationError('Transaction date is required.')

    return transaction_date
```

- [ ] **Step 4: Limit status choices in form (no CANCELLED in create/edit)**

In `__init__`, add after the existing setup:

```python
# Limit status choices — user can only set PENDING or CONFIRMED
# CANCELLED is set via dedicated cancel action
self.fields['status'].choices = [
    ('PENDING', 'Pendente'),
    ('CONFIRMED', 'Efetivada'),
]
```

- [ ] **Step 5: Add status filter to TransactionFilterForm**

In `TransactionFilterForm`, add field after `transaction_type`:

```python
status = forms.ChoiceField(
    choices=[
        ('', 'Todos os status'),
        ('PENDING', 'Pendentes'),
        ('CONFIRMED', 'Efetivadas'),
        ('CANCELLED', 'Canceladas'),
    ],
    required=False,
    label='Status',
    widget=forms.Select(attrs={
        'class': 'form-select',
        'aria-label': 'Filtrar por status',
    })
)
```

In `get_filters()`, add:

```python
# Status filter
if self.cleaned_data.get('status'):
    filters['status'] = self.cleaned_data['status']
```

- [ ] **Step 6: Commit**

```bash
git add transactions/forms.py
git commit -m "feat(forms): add status and auto_confirm fields to transaction forms

Users can choose PENDING or CONFIRMED at creation. Filter form
supports status filtering. Future dates now allowed."
```

---

### Task 5: Views — Confirm, Cancel, and Bulk actions

**Files:**
- Modify: `transactions/views.py`
- Modify: `transactions/urls.py`

- [ ] **Step 1: Add confirm view**

Add to `transactions/views.py`:

```python
from django.views import View
from django.http import Http404


class TransactionConfirmView(LoginRequiredMixin, View):
    """POST: confirm a pending transaction."""

    def post(self, request, pk):
        transaction = get_object_or_404(
            Transaction, pk=pk, user=request.user, status='PENDING'
        )
        transaction.status = 'CONFIRMED'
        transaction.confirmed_at = timezone.now()
        transaction.save()

        messages.success(
            request,
            f'Transação "{transaction.description}" efetivada com sucesso!'
        )

        next_url = request.POST.get('next', reverse('transactions:list'))
        return redirect(next_url)
```

- [ ] **Step 2: Add cancel view**

```python
class TransactionCancelView(LoginRequiredMixin, View):
    """POST: cancel a pending or confirmed transaction."""

    def post(self, request, pk):
        transaction = get_object_or_404(
            Transaction, pk=pk, user=request.user
        )

        if transaction.status == 'CANCELLED':
            messages.error(request, 'Transação já está cancelada.')
            return redirect(reverse('transactions:detail', kwargs={'pk': pk}))

        transaction.status = 'CANCELLED'
        transaction.save()

        messages.success(
            request,
            f'Transação "{transaction.description}" cancelada.'
        )

        next_url = request.POST.get('next', reverse('transactions:list'))
        return redirect(next_url)
```

- [ ] **Step 3: Add bulk confirm view**

```python
class TransactionBulkConfirmView(LoginRequiredMixin, View):
    """POST: confirm multiple pending transactions at once."""

    def post(self, request):
        ids = request.POST.getlist('transaction_ids')
        if not ids:
            messages.warning(request, 'Nenhuma transação selecionada.')
            return redirect(reverse('transactions:list'))

        transactions = Transaction.objects.filter(
            pk__in=ids, user=request.user, status='PENDING'
        )

        count = 0
        for txn in transactions:
            txn.status = 'CONFIRMED'
            txn.confirmed_at = timezone.now()
            txn.save()
            count += 1

        messages.success(request, f'{count} transação(ões) efetivada(s).')
        return redirect(reverse('transactions:list'))
```

- [ ] **Step 4: Update TransactionListView default filter**

In `TransactionListView.get_queryset()`, add default status filter when no status filter is applied:

```python
# Default: hide cancelled unless explicitly filtered
if not self.request.GET.get('status'):
    queryset = queryset.exclude(status='CANCELLED')
```

Add this after the existing filter logic is applied.

- [ ] **Step 5: Update URLs**

In `transactions/urls.py`, add before the `stats/` path:

```python
path('<int:pk>/confirm/', views.TransactionConfirmView.as_view(), name='confirm'),
path('<int:pk>/cancel/', views.TransactionCancelView.as_view(), name='cancel'),
path('bulk-confirm/', views.TransactionBulkConfirmView.as_view(), name='bulk_confirm'),
```

- [ ] **Step 6: Commit**

```bash
git add transactions/views.py transactions/urls.py
git commit -m "feat(views): add confirm, cancel, and bulk-confirm actions

POST-only views with proper user isolation. Default list hides
cancelled transactions unless explicitly filtered."
```

---

### Task 6: Management Command — Auto-confirm pending transactions

**Files:**
- Create: `transactions/management/__init__.py`
- Create: `transactions/management/commands/__init__.py`
- Create: `transactions/management/commands/confirm_pending_transactions.py`

- [ ] **Step 1: Create package structure**

```bash
mkdir -p transactions/management/commands
touch transactions/management/__init__.py
touch transactions/management/commands/__init__.py
```

- [ ] **Step 2: Write the management command**

Create `transactions/management/commands/confirm_pending_transactions.py`:

```python
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from transactions.models import Transaction


class Command(BaseCommand):
    help = 'Efetiva transações pendentes com auto_confirm=True e transaction_date <= hoje'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria efetivado sem alterar dados',
        )

    def handle(self, *args, **options):
        today = date.today()
        dry_run = options['dry_run']

        pending = Transaction.objects.filter(
            status='PENDING',
            auto_confirm=True,
            transaction_date__lte=today,
        ).select_related('account', 'user')

        count = pending.count()

        if count == 0:
            self.stdout.write('Nenhuma transação pendente para efetivar.')
            return

        if dry_run:
            self.stdout.write(f'[DRY RUN] {count} transações seriam efetivadas:')
            for txn in pending:
                self.stdout.write(f'  - {txn.id}: {txn.description} ({txn.amount}) @ {txn.transaction_date}')
            return

        confirmed = 0
        errors = 0
        for txn in pending:
            try:
                txn.status = 'CONFIRMED'
                txn.confirmed_at = timezone.now()
                txn.save()
                confirmed += 1
            except Exception as e:
                errors += 1
                self.stderr.write(f'Erro ao efetivar transação {txn.id}: {e}')

        self.stdout.write(
            self.style.SUCCESS(f'{confirmed} transação(ões) efetivada(s).')
        )
        if errors:
            self.stdout.write(
                self.style.ERROR(f'{errors} erro(s) durante efetivação.')
            )
```

- [ ] **Step 3: Test the command**

Run: `python manage.py confirm_pending_transactions --dry-run`
Expected: "Nenhuma transação pendente para efetivar." (no pending with auto_confirm yet)

- [ ] **Step 4: Commit**

```bash
git add transactions/management/
git commit -m "feat(commands): add confirm_pending_transactions management command

Supports --dry-run flag. Designed to run via cron daily."
```

---

### Task 7: Tests — Status-aware signal and view tests

**Files:**
- Modify: `transactions/tests.py`

- [ ] **Step 1: Update existing test_future_date_validation**

The test `test_future_date_validation` should be removed or converted to test that future dates ARE allowed:

```python
def test_future_date_allowed(self):
    """Test that transaction date can be in the future (for pending transactions)."""
    transaction = Transaction(
        user=self.user,
        account=self.account,
        category=self.expense_category,
        transaction_type='EXPENSE',
        amount=Decimal('100.00'),
        description='Future bill',
        transaction_date=date.today() + timedelta(days=30),
        status='PENDING',
    )
    transaction.full_clean()  # Should NOT raise
```

- [ ] **Step 2: Add status transition tests**

```python
class TransactionStatusTest(TestCase):
    """Test cases for transaction status transitions and balance impact."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='statustest@example.com',
            password='testpass123'
        )
        self.account = Account.objects.create(
            user=self.user,
            name='Status Test Account',
            account_type='checking',
            balance=Decimal('1000.00'),
            currency='BRL'
        )
        self.expense_category = Category.objects.create(
            user=self.user,
            name='Bills',
            category_type='EXPENSE',
            color='#EF4444',
            icon='🍔'
        )
        self.income_category = Category.objects.create(
            user=self.user,
            name='Salary',
            category_type='INCOME',
            color='#10B981',
            icon='💰'
        )

    def test_pending_transaction_does_not_affect_balance(self):
        """Creating a PENDING transaction should not change account balance."""
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('200.00'),
            description='Pending bill',
            transaction_date=date.today() + timedelta(days=5),
            status='PENDING',
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

    def test_confirmed_transaction_affects_balance(self):
        """Creating a CONFIRMED transaction should update account balance."""
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('200.00'),
            description='Confirmed expense',
            transaction_date=date.today(),
            status='CONFIRMED',
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('800.00'))

    def test_confirm_pending_updates_balance(self):
        """Transitioning PENDING → CONFIRMED should apply balance delta."""
        txn = Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('150.00'),
            description='Bill to confirm',
            transaction_date=date.today(),
            status='PENDING',
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

        txn.status = 'CONFIRMED'
        txn.confirmed_at = date.today()
        txn.save()

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('850.00'))

    def test_cancel_confirmed_reverses_balance(self):
        """Transitioning CONFIRMED → CANCELLED should reverse balance delta."""
        txn = Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('300.00'),
            description='Expense to cancel',
            transaction_date=date.today(),
            status='CONFIRMED',
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('700.00'))

        txn.status = 'CANCELLED'
        txn.save()

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

    def test_cancel_pending_no_balance_impact(self):
        """Transitioning PENDING → CANCELLED should not affect balance."""
        txn = Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('500.00'),
            description='Pending to cancel',
            transaction_date=date.today() + timedelta(days=10),
            status='PENDING',
        )
        txn.status = 'CANCELLED'
        txn.save()

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

    def test_invalid_transition_cancelled_to_confirmed(self):
        """CANCELLED → CONFIRMED should raise ValidationError."""
        txn = Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('100.00'),
            description='Cancelled transaction',
            transaction_date=date.today(),
            status='PENDING',
        )
        txn.status = 'CANCELLED'
        txn.save()

        with self.assertRaises(ValidationError):
            txn.status = 'CONFIRMED'
            txn.full_clean()

    def test_delete_pending_no_balance_impact(self):
        """Deleting a PENDING transaction should not affect balance."""
        txn = Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('250.00'),
            description='Pending to delete',
            transaction_date=date.today(),
            status='PENDING',
        )
        txn.delete()
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

    def test_delete_confirmed_reverses_balance(self):
        """Deleting a CONFIRMED transaction should reverse balance."""
        txn = Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('250.00'),
            description='Confirmed to delete',
            transaction_date=date.today(),
            status='CONFIRMED',
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('750.00'))

        txn.delete()
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

    def test_monthly_summary_only_counts_confirmed(self):
        """get_monthly_summary should only include CONFIRMED transactions."""
        today = date.today()
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.income_category,
            transaction_type='INCOME',
            amount=Decimal('3000.00'),
            description='Salary',
            transaction_date=today,
            status='CONFIRMED',
        )
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.expense_category,
            transaction_type='EXPENSE',
            amount=Decimal('500.00'),
            description='Pending rent',
            transaction_date=today,
            status='PENDING',
        )

        summary = Transaction.get_monthly_summary(self.user, today.year, today.month)
        self.assertEqual(summary['income'], Decimal('3000.00'))
        self.assertEqual(summary['expenses'], Decimal('0.00'))
        self.assertEqual(summary['transaction_count'], 1)
```

- [ ] **Step 3: Run all tests**

Run: `python manage.py test transactions`
Expected: All tests pass (existing tests may need the status='CONFIRMED' kwarg added to their Transaction.objects.create calls)

- [ ] **Step 4: Fix any existing tests that break**

Existing tests create transactions without `status` — they'll default to `PENDING` now. Update all `Transaction.objects.create()` calls in `TransactionModelTest` and `TransactionSignalsTest` to include `status='CONFIRMED'` so they maintain their original behavior.

- [ ] **Step 5: Commit**

```bash
git add transactions/tests.py
git commit -m "test(transactions): add comprehensive status transition tests

Covers: balance impact per status, transitions, invalid transitions,
delete behavior, monthly summary filtering. Updates existing tests
to explicitly set status='CONFIRMED'."
```

---

### Task 8: Templates — Status UI in list, form, and detail

**Files:**
- Modify: `templates/transactions/transaction_list.html`
- Modify: `templates/transactions/transaction_form.html`
- Modify: `templates/transactions/transaction_detail.html`

- [ ] **Step 1: Add status badge component**

In `transaction_list.html`, inside each transaction card (`.tx-card`), add a status badge. Find the transaction amount display and add before it:

```html
<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border {{ transaction.status_badge_classes }}">
    {% if transaction.status == 'PENDING' %}⏳{% elif transaction.status == 'CONFIRMED' %}✓{% else %}✕{% endif %}
    {{ transaction.get_status_display }}
</span>
```

- [ ] **Step 2: Add action buttons for pending transactions in list**

After the status badge in each card, add action buttons:

```html
{% if transaction.is_pending %}
<form method="post" action="{% url 'transactions:confirm' transaction.pk %}" class="inline">
    {% csrf_token %}
    <input type="hidden" name="next" value="{{ request.get_full_path }}">
    <button type="submit" class="text-xs px-2 py-1 rounded bg-green-700/50 text-green-300 hover:bg-green-700/80 transition-colors" title="Efetivar">
        ✓ Efetivar
    </button>
</form>
<form method="post" action="{% url 'transactions:cancel' transaction.pk %}" class="inline">
    {% csrf_token %}
    <input type="hidden" name="next" value="{{ request.get_full_path }}">
    <button type="submit" class="text-xs px-2 py-1 rounded bg-red-700/50 text-red-300 hover:bg-red-700/80 transition-colors" title="Cancelar"
            onclick="return confirm('Cancelar esta transação?')">
        ✕ Cancelar
    </button>
</form>
{% elif transaction.is_confirmed %}
<form method="post" action="{% url 'transactions:cancel' transaction.pk %}" class="inline">
    {% csrf_token %}
    <input type="hidden" name="next" value="{{ request.get_full_path }}">
    <button type="submit" class="text-xs px-2 py-1 rounded bg-gray-700/50 text-gray-300 hover:bg-gray-700/80 transition-colors" title="Cancelar"
            onclick="return confirm('Cancelar esta transação efetivada? O saldo será revertido.')">
        ✕ Cancelar
    </button>
</form>
{% endif %}
```

- [ ] **Step 3: Add status filter tabs to list header**

In `transaction_list.html`, after the header section, add filter tabs:

```html
<nav class="flex gap-2 mb-4 overflow-x-auto" aria-label="Filtro por status">
    {% with current_status=request.GET.status %}
    <a href="?{% if request.GET.transaction_type %}transaction_type={{ request.GET.transaction_type }}&{% endif %}"
       class="filter-chip {% if not current_status %}bg-sky-500/20 border-sky-400{% endif %}">
        Todas
    </a>
    <a href="?status=PENDING{% if request.GET.transaction_type %}&transaction_type={{ request.GET.transaction_type }}{% endif %}"
       class="filter-chip {% if current_status == 'PENDING' %}bg-yellow-500/20 border-yellow-400{% endif %}">
        ⏳ Pendentes
    </a>
    <a href="?status=CONFIRMED{% if request.GET.transaction_type %}&transaction_type={{ request.GET.transaction_type }}{% endif %}"
       class="filter-chip {% if current_status == 'CONFIRMED' %}bg-green-500/20 border-green-400{% endif %}">
        ✓ Efetivadas
    </a>
    <a href="?status=CANCELLED{% if request.GET.transaction_type %}&transaction_type={{ request.GET.transaction_type }}{% endif %}"
       class="filter-chip {% if current_status == 'CANCELLED' %}bg-gray-500/20 border-gray-400{% endif %}">
        ✕ Canceladas
    </a>
    {% endwith %}
</nav>
```

- [ ] **Step 4: Add status field to transaction_form.html**

After the transaction_date field group, add:

```html
{# ─── Status ─────────────────────────────────────────── #}
<div class="space-y-1.5">
    <label for="id_status" class="block text-sm font-medium text-gray-300">Status</label>
    <div class="flex gap-2" role="radiogroup" aria-label="Status da transação" id="status-segmented">
        <button type="button" data-value="PENDING"
                class="status-btn flex-1 py-2.5 px-4 rounded-lg text-sm font-medium border-2 transition-all
                       border-yellow-700/50 text-yellow-300 bg-yellow-900/30
                       aria-pressed:border-yellow-400 aria-pressed:bg-yellow-900/60"
                aria-pressed="true">
            ⏳ Pendente
        </button>
        <button type="button" data-value="CONFIRMED"
                class="status-btn flex-1 py-2.5 px-4 rounded-lg text-sm font-medium border-2 transition-all
                       border-green-700/50 text-green-300 bg-green-900/30
                       aria-pressed:border-green-400 aria-pressed:bg-green-900/60"
                aria-pressed="false">
            ✓ Efetivada
        </button>
    </div>
    {{ form.status }}
    {% if form.status.errors %}
    <p class="text-red-400 text-xs mt-1">{{ form.status.errors.0 }}</p>
    {% endif %}
</div>

{# ─── Auto-confirm (visible only when PENDING) ──────── #}
<div class="space-y-1.5" id="auto-confirm-wrapper">
    <label class="flex items-center gap-3 cursor-pointer">
        {{ form.auto_confirm }}
        <span class="text-sm text-gray-300">Efetivar automaticamente na data</span>
    </label>
    {% if form.auto_confirm.errors %}
    <p class="text-red-400 text-xs mt-1">{{ form.auto_confirm.errors.0 }}</p>
    {% endif %}
</div>
```

- [ ] **Step 5: Add JS for status segmented control**

At the bottom of `transaction_form.html` (in the script block), add:

```javascript
// Status segmented control
(function() {
    const statusInput = document.getElementById('id_status');
    const buttons = document.querySelectorAll('.status-btn');
    const autoConfirmWrapper = document.getElementById('auto-confirm-wrapper');

    function updateStatus(value) {
        statusInput.value = value;
        buttons.forEach(btn => {
            btn.setAttribute('aria-pressed', btn.dataset.value === value);
        });
        // Show auto_confirm only for PENDING
        if (autoConfirmWrapper) {
            autoConfirmWrapper.style.display = value === 'PENDING' ? '' : 'none';
        }
    }

    buttons.forEach(btn => {
        btn.addEventListener('click', () => updateStatus(btn.dataset.value));
    });

    // Initialize from current value
    if (statusInput) {
        updateStatus(statusInput.value || 'PENDING');
    }
})();
```

- [ ] **Step 6: Add status display to transaction_detail.html**

In the detail template, add status info in the transaction details section:

```html
<div class="flex items-center gap-2">
    <span class="text-sm text-gray-400">Status:</span>
    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-sm font-medium border {{ transaction.status_badge_classes }}">
        {% if transaction.status == 'PENDING' %}⏳{% elif transaction.status == 'CONFIRMED' %}✓{% else %}✕{% endif %}
        {{ transaction.get_status_display }}
    </span>
    {% if transaction.confirmed_at %}
    <span class="text-xs text-gray-500">em {{ transaction.confirmed_at|date:"d/m/Y H:i" }}</span>
    {% endif %}
</div>

{% if transaction.is_pending %}
<div class="flex gap-2 mt-3">
    <form method="post" action="{% url 'transactions:confirm' transaction.pk %}">
        {% csrf_token %}
        <button type="submit" class="px-4 py-2 rounded-lg bg-green-700/60 text-green-200 hover:bg-green-700 transition-colors font-medium text-sm">
            ✓ Efetivar
        </button>
    </form>
    <form method="post" action="{% url 'transactions:cancel' transaction.pk %}">
        {% csrf_token %}
        <button type="submit" class="px-4 py-2 rounded-lg bg-red-700/60 text-red-200 hover:bg-red-700 transition-colors font-medium text-sm"
                onclick="return confirm('Cancelar esta transação?')">
            ✕ Cancelar
        </button>
    </form>
</div>
{% elif transaction.is_confirmed %}
<div class="mt-3">
    <form method="post" action="{% url 'transactions:cancel' transaction.pk %}">
        {% csrf_token %}
        <button type="submit" class="px-4 py-2 rounded-lg bg-gray-700/60 text-gray-300 hover:bg-gray-700 transition-colors font-medium text-sm"
                onclick="return confirm('Cancelar esta transação efetivada? O saldo será revertido.')">
            ✕ Cancelar transação
        </button>
    </form>
</div>
{% endif %}
```

- [ ] **Step 7: Commit**

```bash
git add templates/transactions/
git commit -m "feat(templates): add status badges, filter tabs, and action buttons

List shows status badges + confirm/cancel buttons per transaction.
Form has segmented control for status + auto_confirm checkbox.
Detail page shows status with confirm/cancel actions."
```

---

### Task 9: Integration — Update existing features to respect status

**Files:**
- Modify: `transactions/views.py` (TransactionStatsView)
- Modify: `budgets/` (if budget queries reference transactions)

- [ ] **Step 1: Update TransactionStatsView to filter CONFIRMED only**

In `TransactionStatsView.get_context_data()`, change the base queryset:

```python
transactions = Transaction.objects.filter(user=self.request.user, status='CONFIRMED')
```

- [ ] **Step 2: Update TransactionListView summary to show both saldos**

In `TransactionListView.get_context_data()`, update the summary calculation:

```python
# Summary for confirmed only
confirmed_txns = self.get_queryset().filter(status='CONFIRMED')
income_total = sum(t.amount for t in confirmed_txns if t.transaction_type == 'INCOME')
expense_total = sum(t.amount for t in confirmed_txns if t.transaction_type == 'EXPENSE')

# Pending summary
pending_txns = Transaction.objects.filter(user=self.request.user, status='PENDING')
pending_income = sum(t.amount for t in pending_txns if t.transaction_type == 'INCOME')
pending_expense = sum(t.amount for t in pending_txns if t.transaction_type == 'EXPENSE')

context.update({
    'total_transactions': transactions.count(),
    'income_total': income_total,
    'expense_total': expense_total,
    'balance': income_total - expense_total,
    'pending_income': pending_income,
    'pending_expense': pending_expense,
    'pending_balance': pending_income - pending_expense,
    'projected_balance': (income_total + pending_income) - (expense_total + pending_expense),
    'has_filters': bool(self.request.GET),
    'accounts_json': self._get_accounts_json(),
})
```

- [ ] **Step 3: Check budgets app for transaction queries**

Run: `grep -n "transaction" budgets/models.py budgets/views.py 2>/dev/null | grep -i "filter\|objects"`

If budget calculations query transactions, add `.filter(status='CONFIRMED')` to those queries.

- [ ] **Step 4: Run full test suite**

Run: `python manage.py test`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add transactions/views.py budgets/
git commit -m "feat(integration): stats and budgets only count CONFIRMED transactions

List view shows confirmed balance + pending/projected balance.
Stats view filters CONFIRMED only. Budget queries updated."
```

---

### Task 10: Final verification and cleanup

- [ ] **Step 1: Run full test suite**

Run: `python manage.py test`
Expected: All tests pass.

- [ ] **Step 2: Run Django check**

Run: `python manage.py check`
Expected: No issues found.

- [ ] **Step 3: Test manually in browser**

1. Start server: `python manage.py runserver`
2. Create a PENDING transaction with future date → verify balance unchanged
3. Create a CONFIRMED transaction → verify balance updated
4. Confirm the pending transaction → verify balance updates
5. Cancel a confirmed transaction → verify balance reverses
6. Check filter tabs work (Pendentes / Efetivadas / Canceladas)
7. Test bulk confirm with multiple pending transactions

- [ ] **Step 4: Run management command test**

Create a pending transaction with `auto_confirm=True` and past date, then:
Run: `python manage.py confirm_pending_transactions --dry-run`
Run: `python manage.py confirm_pending_transactions`
Verify: Transaction status changed to CONFIRMED, balance updated.

- [ ] **Step 5: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore(fin-14): final cleanup and verification"
```

---

## Execution Order Summary

| Task | Description | Depends on |
|------|-------------|-----------|
| 1 | Model fields + validation | — |
| 2 | Data migration | 1 |
| 3 | Signals refactor | 1 |
| 4 | Forms update | 1 |
| 5 | Views + URLs | 1, 3 |
| 6 | Management command | 1 |
| 7 | Tests | 1, 2, 3 |
| 8 | Templates | 4, 5 |
| 9 | Integration (stats, budgets) | 3 |
| 10 | Final verification | All |

Tasks 3, 4, 5, 6 can be parallelized after Task 1+2 complete.
