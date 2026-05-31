from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from decimal import Decimal
from datetime import date

User = get_user_model()


class Transaction(models.Model):
    """
    Transaction model representing financial movements (income and expenses).
    
    This model stores all financial transactions for users, including both income
    and expenses. Each transaction is linked to a specific account and categorized
    for better financial organization. The model supports recurring transactions
    and automatic account balance updates through Django signals.
    
    Schema from PRD:
    - ForeignKeys to User, Account, Category for data relationships
    - Transaction type (INCOME/EXPENSE) for classification
    - Amount with decimal precision for financial accuracy
    - Description and notes for transaction details
    - Transaction date for temporal organization
    - Recurring transaction support with recurrence patterns
    - Timestamps for audit trail
    
    Features:
    - User-scoped data isolation for security
    - Automatic account balance updates via signals
    - Support for recurring transactions
    - Comprehensive validation rules
    - Optimized querying with proper indexing
    """
    
    # Transaction type choices for income vs expense classification
    TRANSACTION_TYPE_CHOICES = [
        ('INCOME', 'Receita'),
        ('EXPENSE', 'Despesa'),
    ]
    
    # Recurrence type choices for recurring transactions
    RECURRENCE_TYPE_CHOICES = [
        ('DAILY', 'Diária'),
        ('WEEKLY', 'Semanal'),
        ('BIWEEKLY', 'Quinzenal'),
        ('MONTHLY', 'Mensal'),
        ('QUARTERLY', 'Trimestral'),
        ('SEMIANNUAL', 'Semestral'),
        ('ANNUAL', 'Anual'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('CONFIRMED', 'Efetivada'),
        ('CANCELLED', 'Cancelada'),
    ]
    
    # Core fields following PRD schema
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text='Owner of this transaction'
    )
    
    account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Conta',
        help_text='Conta bancária ou cartão onde a transação foi realizada'
    )
    
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Categoria',
        help_text='Categoria para organização e relatórios'
    )

    tags = models.ManyToManyField(
        'tags.Tag',
        blank=True,
        related_name='transactions',
        verbose_name='Tags',
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name='Tipo',
        help_text='Se esta transação é uma receita ou despesa'
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor',
        help_text='Valor da transação (sempre positivo)'
    )
    
    description = models.CharField(
        max_length=200,
        verbose_name='Descrição',
        help_text='Descrição breve da transação'
    )
    
    transaction_date = models.DateField(
        verbose_name='Data da Transação',
        help_text='Data em que a transação foi realizada'
    )
    
    # Optional fields
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações',
        help_text='Observações adicionais sobre a transação (opcional)'
    )
    
    is_recurring = models.BooleanField(
        default=False,
        verbose_name='Recorrente',
        help_text='Se esta transação se repete automaticamente'
    )
    
    recurrence_type = models.CharField(
        max_length=15,
        choices=RECURRENCE_TYPE_CHOICES,
        blank=True,
        null=True,
        verbose_name='Tipo de Recorrência',
        help_text='Frequência de repetição (apenas para transações recorrentes)'
    )

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

    # Timestamps for audit trail
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criada em',
        help_text='Quando esta transação foi registrada no sistema'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizada em',
        help_text='Quando esta transação foi modificada pela última vez'
    )
    
    class Meta:
        ordering = ['-transaction_date', '-created_at']
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        
        # Add indexes for common queries
        indexes = [
            models.Index(fields=['user', 'transaction_date']),
            models.Index(fields=['user', 'account']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['transaction_date', 'transaction_type']),
            models.Index(fields=['account', 'transaction_date']),
            models.Index(fields=['category', 'transaction_date']),
            models.Index(fields=['is_recurring']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'transaction_date', 'auto_confirm']),
        ]
    
    def __str__(self):
        """Return string representation with essential transaction info."""
        type_symbol = '+' if self.transaction_type == 'INCOME' else '-'
        return f"{type_symbol} {self.amount} - {self.description} ({self.transaction_date})"
    
    def clean(self):
        """Perform model-level validation."""
        super().clean()
        
        # Validate description is not empty after stripping whitespace
        if not self.description or not self.description.strip():
            raise ValidationError({'description': 'Transaction description cannot be empty.'})
        
        # Clean the description by stripping whitespace
        self.description = self.description.strip()
        
        # Validate amount is positive
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Transaction amount must be positive.'})

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

        # Validate user data consistency - only if user is set
        # Note: During form validation, the user might not be set yet
        try:
            user = getattr(self, 'user', None)
            if user:
                # Check account ownership - use account_id to avoid RelatedObjectDoesNotExist
                if self.account_id:
                    try:
                        account = self.account
                        if hasattr(account, 'user') and account.user != user:
                            raise ValidationError({
                                'account': 'Selected account must belong to the same user.'
                            })
                    except (AttributeError, ObjectDoesNotExist):
                        # Only catch relationship errors, not ValidationError
                        pass
                
                # Check category ownership - use category_id to avoid RelatedObjectDoesNotExist
                if self.category_id:
                    try:
                        category = self.category
                        if hasattr(category, 'user') and category.user != user:
                            raise ValidationError({
                                'category': 'Selected category must belong to the same user.'
                            })
                    except (AttributeError, ObjectDoesNotExist):
                        # Only catch relationship errors, not ValidationError
                        pass
        except (AttributeError, ObjectDoesNotExist):
            # If user relationship doesn't exist yet, skip user validation
            # This happens during form validation before user is assigned
            pass
        
        # Validate account is active - use account_id to avoid RelatedObjectDoesNotExist
        if self.account_id:
            try:
                account = self.account
                if hasattr(account, 'is_active') and not account.is_active:
                    raise ValidationError({
                        'account': 'Cannot create transactions for inactive accounts.'
                    })
            except (AttributeError, ObjectDoesNotExist):
                # If we can't access the account relationship, skip validation
                pass
        
        # Validate category is active and matches transaction type
        # Use category_id to check if category is set, avoiding RelatedObjectDoesNotExist
        if self.category_id:
            try:
                category = self.category
                if hasattr(category, 'is_active') and not category.is_active:
                    raise ValidationError({
                        'category': 'Cannot use inactive categories for transactions.'
                    })
                
                # Ensure category type matches transaction type
                if (hasattr(category, 'category_type') and 
                    self.transaction_type == 'INCOME' and 
                    category.category_type != 'INCOME'):
                    raise ValidationError({
                        'category': 'Income transactions must use income categories.'
                    })
                
                if (hasattr(category, 'category_type') and 
                    self.transaction_type == 'EXPENSE' and 
                    category.category_type != 'EXPENSE'):
                    raise ValidationError({
                        'category': 'Expense transactions must use expense categories.'
                    })
            except (AttributeError, ObjectDoesNotExist):
                # If we can't access the category relationship, skip validation
                # This can happen during form processing before relationships are fully set
                pass
        
        # Validate recurring transaction fields
        if self.is_recurring and not self.recurrence_type:
            raise ValidationError({
                'recurrence_type': 'Recurring transactions must specify a recurrence type.'
            })
        
        if not self.is_recurring and self.recurrence_type:
            raise ValidationError({
                'recurrence_type': 'Recurrence type should only be set for recurring transactions.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to ensure clean() validation is called."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def amount_display(self):
        """Return formatted amount with currency symbol in Brazilian format."""
        if not self.account:
            return f"R$ {float(self.amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'BRL': 'R$',
            'GBP': '£',
            'CAD': 'C$',
        }
        symbol = currency_symbols.get(self.account.currency, self.account.currency)
        
        # Format number in Brazilian style: 1.234,56
        formatted_amount = f"{float(self.amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        return f"{symbol} {formatted_amount}"
    
    @property
    def amount_with_sign(self):
        """Return amount with appropriate sign for transaction type."""
        if self.transaction_type == 'INCOME':
            return self.amount
        else:  # EXPENSE
            return -self.amount
    
    @property
    def amount_with_sign_display(self):
        """Return formatted amount with sign and currency."""
        sign = '+' if self.transaction_type == 'INCOME' else '-'
        return f"{sign} {self.amount_display}"
    
    @property
    def type_display_color(self):
        """Return CSS color class based on transaction type."""
        return 'text-green-500' if self.transaction_type == 'INCOME' else 'text-red-500'
    
    @property
    def is_today(self):
        """Return True if transaction date is today."""
        return self.transaction_date == date.today()
    
    @property
    def days_ago(self):
        """Return number of days since transaction date."""
        return (date.today() - self.transaction_date).days

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

    def get_absolute_url(self):
        """Return the absolute URL to view this transaction."""
        from django.urls import reverse
        return reverse('transactions:detail', kwargs={'pk': self.pk})
    
    @classmethod
    def get_user_transactions(cls, user, **filters):
        """
        Return queryset of transactions for a specific user with optional filters.
        
        Args:
            user: User object
            **filters: Additional filters (account, category, transaction_type, etc.)
            
        Returns:
            QuerySet of user's transactions with related objects prefetched
        """
        queryset = cls.objects.filter(user=user).select_related(
            'account', 'category'
        )
        
        # Apply additional filters
        for field, value in filters.items():
            if value is not None:
                queryset = queryset.filter(**{field: value})
        
        return queryset
    
    @classmethod
    def get_monthly_summary(cls, user, year, month):
        """
        Get monthly summary of transactions for a user.
        
        Args:
            user: User object
            year: Year as integer
            month: Month as integer (1-12)
            
        Returns:
            Dictionary with income, expenses, and balance totals
        """
        from django.db.models import Sum, Q
        
        transactions = cls.objects.filter(
            user=user,
            transaction_date__year=year,
            transaction_date__month=month,
            status='CONFIRMED',
        )
        
        income_total = transactions.filter(
            transaction_type='INCOME'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        expense_total = transactions.filter(
            transaction_type='EXPENSE'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        return {
            'income': income_total,
            'expenses': expense_total,
            'balance': income_total - expense_total,
            'transaction_count': transactions.count()
        }
