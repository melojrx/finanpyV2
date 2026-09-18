"""Atomic account-domain operations shared by DRF and the web application."""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Account, AccountBalanceAdjustment, FundTransfer


def adjust_account_balance(
    *, user, account_id, new_balance, adjustment_date, reason, client_id
):
    """Set a reserve balance and retain an immutable audit entry.

    An identical retry returns its first result. Reusing the key for a different
    operation is rejected instead of silently changing the balance twice.
    """
    with transaction.atomic():
        existing = (
            AccountBalanceAdjustment.objects.select_for_update()
            .filter(user=user, client_id=client_id)
            .first()
        )
        if existing:
            same_request = (
                existing.account_id == account_id
                and existing.new_balance == new_balance
                and existing.adjustment_date == adjustment_date
                and existing.reason == reason.strip()
            )
            if same_request:
                return existing
            raise ValidationError('client_id já foi usado em outro ajuste.')

        account = Account.objects.select_for_update().get(pk=account_id, user=user)
        if account.account_type not in {'savings', 'investment'}:
            raise ValidationError({
                'account': 'Ajustes manuais só são permitidos para reservas ou investimentos.'
            })

        previous_balance = account.balance
        adjustment = AccountBalanceAdjustment.objects.create(
            user=user,
            account=account,
            previous_balance=previous_balance,
            new_balance=new_balance,
            delta=new_balance - previous_balance,
            adjustment_date=adjustment_date,
            reason=reason,
            client_id=client_id,
        )
        account.balance = new_balance
        account.save(update_fields=['balance', 'updated_at'])
        return adjustment


def create_transfer(
    *, user, source_account, target_account, amount, transfer_date,
    description='', destination_context='', client_id=''
):
    """Create an internal transfer, returning the original on an identical retry."""
    with transaction.atomic():
        existing = None
        if client_id:
            existing = FundTransfer.objects.select_for_update().filter(
                user=user, client_id=client_id
            ).first()
        if existing:
            if (
                existing.from_account_id == source_account.id
                and existing.to_account_id == target_account.id
                and existing.amount == amount
                and existing.transfer_date == transfer_date
                and existing.description == (description or '').strip()
                and existing.destination_context == (destination_context or '').strip()
            ):
                return existing, False
            raise ValidationError('client_id já foi usado em outra transferência.')

        transfer = FundTransfer(
            user=user, from_account=source_account, to_account=target_account,
            amount=amount, transfer_date=transfer_date,
            description=(description or '').strip(),
            destination_context=(destination_context or '').strip(),
            client_id=client_id or '',
        )
        transfer.save()
        return transfer, True
