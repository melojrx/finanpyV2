from decimal import Decimal

from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Goal, GoalContribution


def _recalculate_goal(goal):
    """Recompute ``current_amount`` and ``status`` for a goal from contributions."""
    total = goal.contributions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    new_status = goal.status
    if goal.status != Goal.STATUS_CANCELLED:
        if total >= goal.target_amount:
            new_status = Goal.STATUS_COMPLETED
        else:
            new_status = Goal.STATUS_ACTIVE

    Goal.objects.filter(pk=goal.pk).update(
        current_amount=total,
        status=new_status,
    )


@receiver(post_save, sender=GoalContribution)
def update_goal_amount_on_save(sender, instance, **kwargs):
    _recalculate_goal(instance.goal)


@receiver(post_delete, sender=GoalContribution)
def update_goal_amount_on_delete(sender, instance, **kwargs):
    try:
        goal = Goal.objects.get(pk=instance.goal_id)
    except Goal.DoesNotExist:
        return
    _recalculate_goal(goal)
