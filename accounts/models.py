from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

User = get_user_model()


class Account(models.Model):
    """
    Account model representing user financial accounts (bank accounts, credit cards, etc.).
    
    This model stores information about user's financial accounts including balances,
    account types, and currency settings. Each account is user-scoped for data isolation.
    
    Schema from PRD:
    - ForeignKey to User for data isolation
    - Name and account type classification
    - Balance tracking with decimal precision
    - Currency support for international users
    - Active/inactive status for account lifecycle management
    - Timestamps for audit trail
    """
    
    # Account type choices based on common financial account types
    ACCOUNT_TYPE_CHOICES = [
        ('checking', 'Conta Corrente'),
        ('savings', 'Conta Poupança'),
        ('credit_card', 'Cartão de Crédito'),
        ('investment', 'Conta de Investimento'),
        ('cash', 'Dinheiro'),
    ]
    
    # Currency choices - can be extended as needed
    CURRENCY_CHOICES = [
        ('USD', 'Dólar Americano'),
        ('EUR', 'Euro'),
        ('BRL', 'Real Brasileiro'),
        ('GBP', 'Libra Esterlina'),
        ('CAD', 'Dólar Canadense'),
    ]
    
    # Core fields following PRD schema
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='accounts',
        help_text='Owner of this account'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nome',
        help_text='Nome descritivo para a conta (ex.: "Conta Corrente Itaú", "Fundo de Emergência")'
    )
    
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        verbose_name='Tipo de Conta',
        help_text='Tipo de conta para categorização e relatórios'
    )
    
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Saldo',
        help_text='Saldo atual da conta'
    )
    
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='BRL',
        verbose_name='Moeda',
        help_text='Código da moeda da conta (ISO 4217)'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativa',
        help_text='Se esta conta está ativa e deve ser incluída nos cálculos'
    )
    
    # Timestamps for audit trail
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criada em',
        help_text='Quando esta conta foi criada'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizada em',
        help_text='Quando esta conta foi modificada pela última vez'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Conta'
        verbose_name_plural = 'Contas'
        # Ensure unique account names per user
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_account_name_per_user'
            )
        ]
        # Add indexes for common queries
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'account_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        """Return string representation showing account name and type."""
        return f"{self.name} ({self.get_account_type_display()})"
    
    def clean(self):
        """Perform model-level validation."""
        super().clean()
        
        # Validate account name is not empty after stripping whitespace
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'Account name cannot be empty.'})
        
        # Clean the name by stripping whitespace
        self.name = self.name.strip()
        
        # For credit cards, balance can be negative (representing debt)
        # For other account types, warn but allow negative balances (overdraft scenarios)
        if self.account_type != 'credit_card' and self.balance < 0:
            # Note: We could add a warning here or handle overdraft logic
            pass
    
    def save(self, *args, **kwargs):
        """Override save to ensure clean() validation is called."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def balance_display(self):
        """Return formatted balance with currency symbol in Brazilian format."""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'BRL': 'R$',
            'GBP': '£',
            'CAD': 'C$',
        }
        symbol = currency_symbols.get(self.currency, self.currency)
        
        # Format number in Brazilian style: 1.234,56
        formatted_balance = f"{float(self.balance):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        return f"{symbol} {formatted_balance}"
    
    @property
    def is_debt_account(self):
        """Return True if this is a debt-type account (credit card)."""
        return self.account_type == 'credit_card'
    
    def get_transactions_queryset(self):
        """Return queryset of transactions for this account."""
        return self.transactions.select_related('category', 'user').order_by('-transaction_date', '-created_at')


class FundTransfer(models.Model):
    """Transferência de fundos entre contas do mesmo usuário.

    Transferências não são receitas nem despesas: apenas movem saldo entre
    contas. O registro existe para auditoria e para permitir conciliação.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fund_transfers',
        help_text='Owner of this transfer',
    )
    from_account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.CASCADE,
        related_name='outgoing_transfers',
        verbose_name='Conta de origem',
    )
    to_account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.CASCADE,
        related_name='incoming_transfers',
        verbose_name='Conta de destino',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor',
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Descrição',
    )
    destination_context = models.CharField(
        max_length=300,
        blank=True,
        default='',
        verbose_name='Contexto de destino',
    )
    client_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='Identificador idempotente',
    )
    transfer_date = models.DateField(verbose_name='Data da transferência')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criada em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizada em')

    class Meta:
        ordering = ['-transfer_date', '-created_at']
        verbose_name = 'Transferência entre contas'
        verbose_name_plural = 'Transferências entre contas'
        indexes = [
            models.Index(fields=['user', 'transfer_date']),
            models.Index(fields=['user', 'from_account']),
            models.Index(fields=['user', 'to_account']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'client_id'],
                condition=~models.Q(client_id=''),
                name='unique_transfer_client_id_per_user',
            ),
        ]

    def __str__(self):
        return (
            f"{self.amount} de {self.from_account.name} "
            f"para {self.to_account.name} ({self.transfer_date})"
        )

    def clean(self):
        super().clean()
        if self.description:
            self.description = self.description.strip()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Transfer amount must be positive.'})
        if self.from_account_id and self.to_account_id:
            if self.from_account_id == self.to_account_id:
                raise ValidationError({
                    'to_account': 'Conta de destino deve ser diferente da origem.'
                })
        if self.user_id:
            if self.from_account_id and self.from_account.user_id != self.user_id:
                raise ValidationError({
                    'from_account': 'Conta de origem não pertence ao usuário.'
                })
            if self.to_account_id and self.to_account.user_id != self.user_id:
                raise ValidationError({
                    'to_account': 'Conta de destino não pertence ao usuário.'
                })
            if self.from_account_id and not self.from_account.is_active:
                raise ValidationError({
                    'from_account': 'Conta de origem está inativa.'
                })
            if self.to_account_id and not self.to_account.is_active:
                raise ValidationError({
                    'to_account': 'Conta de destino está inativa.'
                })

    def save(self, *args, **kwargs):
        if not self._state.adding:
            original = type(self).objects.get(pk=self.pk)
            if (
                self.from_account_id != original.from_account_id
                or self.to_account_id != original.to_account_id
                or self.amount != original.amount
            ):
                raise ValidationError(
                    'Contas e valor de uma transferência não podem ser alterados.'
                )

            self.full_clean()
            return super().save(*args, **kwargs)

        from django.db import transaction

        with transaction.atomic():
            # Bloqueia as contas numa ordem estável para evitar deadlock.
            account_ids = sorted([self.from_account_id, self.to_account_id])
            locked = {
                account.pk: account
                for account in Account.objects.select_for_update().filter(
                    pk__in=account_ids
                ).order_by('pk')
            }
            from_locked = locked[self.from_account_id]
            to_locked = locked[self.to_account_id]

            self.from_account = from_locked
            self.to_account = to_locked
            self.full_clean()

            from_locked.balance -= self.amount
            to_locked.balance += self.amount
            from_locked.save(update_fields=['balance'])
            to_locked.save(update_fields=['balance'])
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.db import transaction

        with transaction.atomic():
            # Mantém a mesma ordem de bloqueio usada na criação.
            account_ids = sorted([self.from_account_id, self.to_account_id])
            locked = {
                account.pk: account
                for account in Account.objects.select_for_update().filter(
                    pk__in=account_ids
                ).order_by('pk')
            }
            from_locked = locked[self.from_account_id]
            to_locked = locked[self.to_account_id]

            result = super().delete(*args, **kwargs)

            from_locked.balance += self.amount
            to_locked.balance -= self.amount
            from_locked.save(update_fields=['balance'])
            to_locked.save(update_fields=['balance'])

        return result

    @classmethod
    def create_and_apply(cls, *, user, from_account, to_account, amount,
                         transfer_date, description=''):
        """Cria a transferência; o save aplica o movimento atomicamente."""
        transfer = cls(
            user=user,
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            transfer_date=transfer_date,
            description=description or '',
        )
        transfer.save()
        return transfer


class AccountBalanceAdjustment(models.Model):
    """Immutable audit record for a manual reserve balance adjustment."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='account_balance_adjustments',
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='balance_adjustments',
    )
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2)
    new_balance = models.DecimalField(max_digits=12, decimal_places=2)
    delta = models.DecimalField(max_digits=12, decimal_places=2)
    adjustment_date = models.DateField()
    reason = models.CharField(max_length=300)
    client_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-adjustment_date', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'client_id'],
                name='unique_account_adjustment_client_id_per_user',
            ),
        ]
        indexes = [
            models.Index(fields=['account', 'adjustment_date']),
            models.Index(fields=['user', 'adjustment_date']),
        ]

    def clean(self):
        super().clean()
        if self.account_id and self.account.account_type not in {
            'savings', 'investment'
        }:
            raise ValidationError({
                'account': 'Ajustes manuais só são permitidos para reservas ou investimentos.'
            })
        if self.account_id and self.user_id and self.account.user_id != self.user_id:
            raise ValidationError({'account': 'Conta não pertence ao usuário.'})
        if self.delta != self.new_balance - self.previous_balance:
            raise ValidationError({'delta': 'Delta deve corresponder aos saldos informado.'})
        self.reason = (self.reason or '').strip()
        if not self.reason:
            raise ValidationError({'reason': 'Motivo do ajuste é obrigatório.'})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Ajustes de saldo são imutáveis.')
        self.full_clean()
        return super().save(*args, **kwargs)
