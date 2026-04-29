"""
Context processors for the budgets app.

Exposes lightweight data needed by base.html (navbar badges, etc.) without
forcing every view to inject it.
"""
from .models import BudgetAlert


def budget_alerts(request):
    """Return the unread alert count for the navbar badge."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'unread_budget_alerts_count': 0}

    return {
        'unread_budget_alerts_count': BudgetAlert.objects
        .unacknowledged_for_user(request.user)
        .count(),
    }
