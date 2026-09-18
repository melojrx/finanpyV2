"""Atomic operations for assets owed to a FinanPy user."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import Account
from .models import LoanReceivable, LoanSettlement


def create_loan_receivable(
    *, user, counterparty, amount, origin_account_id, loan_date, description,
    expected_return_date, client_id
):
    with transaction.atomic():
        existing = LoanReceivable.objects.select_for_update().filter(
            user=user, client_id=client_id
        ).first()
        if existing:
            if (
                existing.counterparty == counterparty.strip()
                and existing.original_amount == amount
                and existing.origin_account_id == origin_account_id
                and existing.loan_date == loan_date
                and existing.description == description.strip()
            ):
                return existing
            raise ValidationError('client_id já foi usado em outro empréstimo.')

        account = Account.objects.select_for_update().get(pk=origin_account_id, user=user)
        loan = LoanReceivable.objects.create(
            user=user, counterparty=counterparty.strip(), original_amount=amount,
            outstanding_amount=amount, origin_account=account, loan_date=loan_date,
            description=description.strip(), expected_return_date=expected_return_date,
            client_id=client_id,
        )
        account.balance -= amount
        account.save(update_fields=['balance', 'updated_at'])
        return loan


def settle_loan_receivable(
    *, user, loan_id, amount, target_account_id, settlement_date, description,
    client_id
):
    with transaction.atomic():
        loan = LoanReceivable.objects.select_for_update().get(pk=loan_id, user=user)
        existing = LoanSettlement.objects.filter(loan=loan, client_id=client_id).first()
        if existing:
            if (
                existing.amount == amount
                and existing.target_account_id == target_account_id
                and existing.settlement_date == settlement_date
            ):
                return existing
            raise ValidationError('client_id já foi usado em outra liquidação.')
        if loan.status != LoanReceivable.STATUS_ACTIVE:
            raise ValidationError('Apenas empréstimos ativos podem ser liquidados.')
        if amount > loan.outstanding_amount:
            raise ValidationError({'amount': 'Valor excede o saldo pendente.'})

        account = Account.objects.select_for_update().get(pk=target_account_id, user=user)
        settlement = LoanSettlement.objects.create(
            loan=loan, target_account=account, amount=amount,
            settlement_date=settlement_date, description=description.strip(),
            client_id=client_id,
        )
        loan.outstanding_amount -= amount
        if loan.outstanding_amount == 0:
            loan.status = LoanReceivable.STATUS_SETTLED
        loan.save(update_fields=['outstanding_amount', 'status', 'updated_at'])
        account.balance += amount
        account.save(update_fields=['balance', 'updated_at'])
        return settlement


def write_off_loan_receivable(*, user, loan_id, reason):
    with transaction.atomic():
        loan = LoanReceivable.objects.select_for_update().get(pk=loan_id, user=user)
        if loan.status != LoanReceivable.STATUS_ACTIVE:
            raise ValidationError('Apenas empréstimos ativos podem ser baixados.')
        reason = (reason or '').strip()
        if not reason:
            raise ValidationError({'reason': 'Motivo da baixa é obrigatório.'})
        loan.status = LoanReceivable.STATUS_WRITTEN_OFF
        loan.written_off_at = timezone.now()
        loan.write_off_reason = reason
        loan.save(update_fields=['status', 'written_off_at', 'write_off_reason', 'updated_at'])
        return loan
