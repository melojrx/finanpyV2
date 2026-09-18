from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class LoanReceivable(models.Model):
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_SETTLED = 'SETTLED'
    STATUS_WRITTEN_OFF = 'WRITTEN_OFF'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Ativo'),
        (STATUS_SETTLED, 'Liquidado'),
        (STATUS_WRITTEN_OFF, 'Baixado como perda'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='loans_receivable')
    counterparty = models.CharField(max_length=150)
    original_amount = models.DecimalField(max_digits=12, decimal_places=2,
                                          validators=[MinValueValidator(Decimal('0.01'))])
    outstanding_amount = models.DecimalField(max_digits=12, decimal_places=2)
    origin_account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT,
                                       related_name='loans_originated')
    loan_date = models.DateField()
    description = models.CharField(max_length=300)
    expected_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                              default=STATUS_ACTIVE)
    client_id = models.CharField(max_length=64)
    written_off_at = models.DateTimeField(null=True, blank=True)
    write_off_reason = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-loan_date', '-created_at']
        constraints = [models.UniqueConstraint(
            fields=['user', 'client_id'], name='unique_loan_client_id_per_user'
        )]
        indexes = [models.Index(fields=['user', 'status'])]

    def clean(self):
        super().clean()
        if self.user_id and self.origin_account_id and self.user_id != self.origin_account.user_id:
            raise ValidationError({'origin_account': 'Conta de origem não pertence ao usuário.'})
        if self.outstanding_amount < 0 or self.outstanding_amount > self.original_amount:
            raise ValidationError({'outstanding_amount': 'Saldo pendente inválido.'})


class LoanSettlement(models.Model):
    loan = models.ForeignKey(LoanReceivable, on_delete=models.PROTECT,
                             related_name='settlements')
    target_account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT,
                                       related_name='loan_settlements_received')
    amount = models.DecimalField(max_digits=12, decimal_places=2,
                                 validators=[MinValueValidator(Decimal('0.01'))])
    settlement_date = models.DateField()
    description = models.CharField(max_length=300, blank=True, default='')
    client_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-settlement_date', '-created_at']
        constraints = [models.UniqueConstraint(
            fields=['loan', 'client_id'], name='unique_settlement_client_id_per_loan'
        )]
