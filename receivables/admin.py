from django.contrib import admin

from .models import LoanReceivable, LoanSettlement


@admin.register(LoanReceivable)
class LoanReceivableAdmin(admin.ModelAdmin):
    list_display = ['counterparty', 'outstanding_amount', 'status', 'loan_date', 'user']
    list_filter = ['status', 'loan_date']
    search_fields = ['counterparty', 'description', 'user__email']
    readonly_fields = [
        'user', 'original_amount', 'outstanding_amount', 'client_id',
        'created_at', 'updated_at', 'written_off_at',
    ]


@admin.register(LoanSettlement)
class LoanSettlementAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'target_account', 'settlement_date']
    readonly_fields = ['loan', 'target_account', 'amount', 'settlement_date', 'description', 'client_id', 'created_at']
