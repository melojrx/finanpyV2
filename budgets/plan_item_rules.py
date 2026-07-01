from decimal import Decimal

from django.db.models import Q, Sum

from categories.models import Category


def get_allocatable_expense_category_ids(user):
    """Return active expense category IDs editable in the distribution UI."""
    active_expense = Category.objects.filter(
        user=user,
        category_type='EXPENSE',
        is_active=True,
    )
    parent_ids_with_active_children = (
        active_expense
        .filter(parent_id__isnull=False)
        .values_list('parent_id', flat=True)
        .distinct()
    )
    return set(
        active_expense
        .filter(
            (
                Q(parent_id__isnull=False) &
                Q(parent__parent_id__isnull=True)
            ) |
            (
                Q(parent_id__isnull=True) &
                ~Q(id__in=parent_ids_with_active_children)
            )
        )
        .values_list('id', flat=True)
    )


def get_allocated_expense_total(plan):
    """Sum only allocatable expense items for ceiling validation."""
    category_ids = get_allocatable_expense_category_ids(plan.user)
    total = (
        plan.items
        .filter(category_id__in=category_ids)
        .aggregate(total=Sum('planned_amount'))['total']
    )
    return total or Decimal('0.00')


def copy_allocatable_plan_items(source_plan, target_plan):
    """Copy only currently allocatable expense items from source to target."""
    category_ids = get_allocatable_expense_category_ids(target_plan.user)
    copied = 0
    source_items = (
        source_plan.items
        .select_related('category')
        .filter(category_id__in=category_ids)
    )
    for src_item in source_items:
        _, created = target_plan.items.get_or_create(
            category=src_item.category,
            defaults={
                'planned_amount': src_item.planned_amount,
                'alert_threshold': src_item.alert_threshold,
            },
        )
        if created:
            copied += 1
    return copied
