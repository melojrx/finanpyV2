"""
Django signals for automatic account balance updates when transactions are modified.

This module implements post_save and post_delete signal handlers that automatically
update account balances when transactions are created, updated, or deleted. The signals
ensure data consistency and eliminate the need for manual balance calculations.

Key Features:
- Automatic balance updates for all transaction operations
- Support for transaction updates (reverses old amount, applies new amount)
- Proper handling of income vs expense transaction types
- Error handling and logging for robustness
- User data isolation and security validation

Signal Flow:
1. Transaction created → Add amount to account balance (income +, expense -)
2. Transaction updated → Reverse old amount, apply new amount
3. Transaction deleted → Reverse amount from account balance
"""

import logging
from decimal import Decimal
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist

# Get logger for this module
logger = logging.getLogger(__name__)

# Dictionary to store old transaction values for update handling
_old_transaction_values = {}


def calculate_balance_delta(transaction_obj):
    """
    Calculate the balance delta (change) for a given transaction.
    
    Args:
        transaction_obj: Transaction instance
        
    Returns:
        Decimal: Positive for income, negative for expense
        
    Business Logic:
    - INCOME transactions increase account balance (+amount)
    - EXPENSE transactions decrease account balance (-amount)
    """
    if transaction_obj.transaction_type == 'INCOME':
        return transaction_obj.amount
    elif transaction_obj.transaction_type == 'EXPENSE':
        return -transaction_obj.amount
    else:
        logger.error(
            f"Unknown transaction type '{transaction_obj.transaction_type}' "
            f"for transaction {transaction_obj.id}"
        )
        return Decimal('0.00')


def update_account_balance(account, delta, operation='add'):
    """
    Update account balance with the given delta.
    
    Args:
        account: Account instance to update
        delta: Decimal amount to add/subtract
        operation: 'add' or 'subtract' - operation to perform
        
    This function:
    - Updates the account balance atomically
    - Handles both positive and negative deltas correctly
    - Logs balance changes for audit purposes
    - Saves the account with updated balance
    """
    try:
        old_balance = account.balance
        
        if operation == 'add':
            account.balance = old_balance + delta
        elif operation == 'subtract':
            account.balance = old_balance - delta
        else:
            logger.error(f"Invalid balance operation: {operation}")
            return
        
        # Save account with updated balance
        # Use update_fields to only update the balance and updated_at timestamp
        account.save(update_fields=['balance', 'updated_at'])
        
        logger.info(
            f"Account {account.id} ({account.name}) balance updated: "
            f"{old_balance} → {account.balance} (delta: {'+' if operation == 'add' else '-'}{abs(delta)})"
        )
        
    except Exception as e:
        logger.error(
            f"Error updating account {account.id} balance: {str(e)}"
        )
        raise


@receiver(pre_save, sender='transactions.Transaction')
def handle_transaction_pre_save(sender, instance, **kwargs):
    """
    Pre-save signal to capture old transaction values before updates.
    
    This signal stores the old transaction values in a module-level dictionary
    so they can be used in the post_save signal to properly handle balance updates.
    
    Args:
        sender: Transaction model class
        instance: Transaction instance being saved
        **kwargs: Additional signal arguments
    """
    try:
        if instance.pk:  # Only for existing transactions (updates)
            try:
                # Get the old transaction from database
                old_transaction = sender.objects.get(pk=instance.pk)
                
                # Store old values for use in post_save
                _old_transaction_values[instance.pk] = {
                    'account_id': old_transaction.account_id,
                    'amount': old_transaction.amount,
                    'transaction_type': old_transaction.transaction_type,
                    'status': old_transaction.status,
                }
                
                logger.debug(f"Stored old values for transaction {instance.pk}")
                
            except ObjectDoesNotExist:
                # Transaction doesn't exist yet, this is a creation
                logger.debug(f"Transaction {instance.pk} not found in database, treating as new")
                
    except Exception as e:
        logger.error(f"Error in transaction pre_save signal for transaction {instance.pk}: {str(e)}")


@receiver(post_save, sender='transactions.Transaction')
def handle_transaction_save(sender, instance, created, **kwargs):
    """
    Signal handler for transaction creation and updates.
    Only CONFIRMED transactions affect account balance.
    """
    try:
        if created:
            if instance.status != 'CONFIRMED':
                logger.info(
                    f"Transaction {instance.id} created as "
                    f"{instance.status}, no balance impact"
                )
                return

            logger.info(
                f"Processing new CONFIRMED transaction "
                f"{instance.id}: {instance}"
            )

            try:
                if not instance.user or not instance.account:
                    logger.error(
                        f"Transaction {instance.id} missing user or account"
                    )
                    return
                if instance.account.user != instance.user:
                    logger.error(
                        f"User mismatch for transaction {instance.id}"
                    )
                    return
            except Exception as e:
                logger.error(
                    f"Error validating relationships for "
                    f"transaction {instance.id}: {e}"
                )
                return

            delta = calculate_balance_delta(instance)
            update_account_balance(instance.account, delta, 'add')

        else:
            logger.info(f"Processing transaction update {instance.id}")

            old_values = _old_transaction_values.pop(instance.pk, None)
            if not old_values:
                logger.warning(
                    f"No old values for transaction {instance.id}, "
                    f"skipping"
                )
                return

            old_status = old_values.get('status', 'CONFIRMED')
            new_status = instance.status

            try:
                # Case 1: Status changed
                if old_status != new_status:
                    if (old_status == 'PENDING'
                            and new_status == 'CONFIRMED'):
                        delta = calculate_balance_delta(instance)
                        update_account_balance(
                            instance.account, delta, 'add'
                        )
                        logger.info(
                            f"Transaction {instance.id} confirmed, "
                            f"balance updated"
                        )

                    elif (old_status == 'CONFIRMED'
                            and new_status == 'CANCELLED'):
                        class MockOld:
                            def __init__(self, v):
                                self.amount = v['amount']
                                self.transaction_type = (
                                    v['transaction_type']
                                )
                        old_delta = calculate_balance_delta(
                            MockOld(old_values)
                        )
                        from accounts.models import Account
                        old_account = Account.objects.get(
                            pk=old_values['account_id']
                        )
                        update_account_balance(
                            old_account, old_delta, 'subtract'
                        )
                        logger.info(
                            f"Transaction {instance.id} cancelled, "
                            f"balance reversed"
                        )

                # Case 2: Still CONFIRMED but amount/type/account changed
                elif new_status == 'CONFIRMED':
                    if (instance.amount != old_values['amount']
                            or instance.transaction_type
                            != old_values['transaction_type']
                            or instance.account_id
                            != old_values['account_id']):

                        class MockOld:
                            def __init__(self, v):
                                self.account_id = v['account_id']
                                self.amount = v['amount']
                                self.transaction_type = (
                                    v['transaction_type']
                                )

                        old_tx = MockOld(old_values)

                        if (instance.account_id
                                != old_values['account_id']):
                            old_delta = calculate_balance_delta(old_tx)
                            from accounts.models import Account
                            old_account = Account.objects.get(
                                pk=old_values['account_id']
                            )
                            update_account_balance(
                                old_account, old_delta, 'subtract'
                            )
                            new_delta = calculate_balance_delta(instance)
                            update_account_balance(
                                instance.account, new_delta, 'add'
                            )
                        else:
                            old_delta = calculate_balance_delta(old_tx)
                            update_account_balance(
                                instance.account, old_delta, 'subtract'
                            )
                            new_delta = calculate_balance_delta(instance)
                            update_account_balance(
                                instance.account, new_delta, 'add'
                            )

            except Exception as e:
                logger.error(
                    f"Error handling transaction update "
                    f"{instance.id}: {e}"
                )

    except Exception as e:
        logger.error(
            f"Error in transaction save signal for "
            f"{instance.id}: {e}"
        )


@receiver(post_delete, sender='transactions.Transaction')
def handle_transaction_delete(sender, instance, **kwargs):
    """
    Signal handler for transaction deletion.
    Only reverses balance for CONFIRMED transactions.
    """
    try:
        if instance.status != 'CONFIRMED':
            logger.info(
                f"Transaction {instance.id} deleted "
                f"(status={instance.status}), no balance impact"
            )
            return

        logger.info(
            f"Processing CONFIRMED transaction deletion {instance.id}"
        )

        if not instance.account:
            logger.warning(
                f"Transaction {instance.id} has no account reference"
            )
            return

        if instance.account.user != instance.user:
            logger.error(
                f"User mismatch on deletion for "
                f"transaction {instance.id}"
            )
            return

        delta = calculate_balance_delta(instance)
        update_account_balance(instance.account, delta, 'subtract')

    except Exception as e:
        logger.error(
            f"Error in transaction delete signal for "
            f"transaction {instance.id}: {e}"
        )


# Additional utility functions for balance reconciliation and debugging

def recalculate_account_balance(account):
    """
    Recalculate account balance from scratch based on all transactions.
    
    This is a utility function for balance reconciliation in case signals
    fail or data gets inconsistent. It should be used sparingly and mainly
    for debugging or data recovery purposes.
    
    Args:
        account: Account instance to recalculate
        
    Returns:
        tuple: (old_balance, new_balance, difference)
    """
    from django.db.models import Sum, Case, When, DecimalField
    
    try:
        old_balance = account.balance
        
        # Calculate total impact of all transactions for this account
        from django.db.models import F
        balance_impact = account.transactions.filter(status='CONFIRMED').aggregate(
            total_impact=Sum(
                Case(
                    When(transaction_type='INCOME', then=F('amount')),
                    When(transaction_type='EXPENSE', then=F('amount') * -1),
                    default=0,
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )['total_impact'] or Decimal('0.00')
        
        # Note: This assumes the account started with 0 balance
        # In a real implementation, you might want to track initial balances
        new_balance = balance_impact
        
        account.balance = new_balance
        account.save(update_fields=['balance', 'updated_at'])
        
        difference = new_balance - old_balance
        
        logger.info(
            f"Recalculated balance for account {account.id} ({account.name}): "
            f"{old_balance} → {new_balance} (difference: {difference})"
        )
        
        return old_balance, new_balance, difference
        
    except Exception as e:
        logger.error(
            f"Error recalculating balance for account {account.id}: {str(e)}"
        )
        raise


def validate_account_balances(user=None):
    """
    Validate that all account balances match their transaction history.
    
    This is a debugging/auditing function to check for balance inconsistencies
    that might occur if signals fail or are bypassed.
    
    Args:
        user: Optional User instance to limit validation to specific user
        
    Returns:
        list: List of accounts with balance discrepancies
    """
    from accounts.models import Account
    from django.db.models import Sum, Case, When, DecimalField
    
    discrepancies = []
    
    try:
        accounts_query = Account.objects.all()
        if user:
            accounts_query = accounts_query.filter(user=user)
            
        for account in accounts_query:
            # Calculate expected balance from transactions
            from django.db.models import F
            expected_balance = account.transactions.filter(
                status='CONFIRMED'
            ).aggregate(
                total_impact=Sum(
                    Case(
                        When(transaction_type='INCOME', then=F('amount')),
                        When(transaction_type='EXPENSE', then=F('amount') * -1),
                        default=0,
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                )
            )['total_impact'] or Decimal('0.00')
            
            if account.balance != expected_balance:
                discrepancy = {
                    'account': account,
                    'current_balance': account.balance,
                    'expected_balance': expected_balance,
                    'difference': account.balance - expected_balance
                }
                discrepancies.append(discrepancy)
                
                logger.warning(
                    f"Balance discrepancy found for account {account.id} ({account.name}): "
                    f"Current: {account.balance}, Expected: {expected_balance}, "
                    f"Difference: {discrepancy['difference']}"
                )
        
        if not discrepancies:
            logger.info(
                f"All account balances validated successfully "
                f"{'for user ' + str(user.id) if user else '(all users)'}"
            )
            
    except Exception as e:
        logger.error(f"Error validating account balances: {str(e)}")
        raise
    
    return discrepancies