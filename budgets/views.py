from calendar import monthrange
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from datetime import date
from decimal import Decimal

from .models import Budget, BudgetAlert, MonthlyPlan, MonthlyPlanItem
from .forms import MonthlyPlanHeaderForm
from .plan_item_rules import (
    copy_allocatable_plan_items,
    get_allocatable_expense_category_ids,
    get_allocated_expense_total,
)
from categories.models import Category

MONTH_NAMES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
}


def _adjacent_months(year, month):
    if month == 1:
        prev = {'year': year - 1, 'month': 12}
    else:
        prev = {'year': year, 'month': month - 1}
    if month == 12:
        next_ = {'year': year + 1, 'month': 1}
    else:
        next_ = {'year': year, 'month': month + 1}
    return prev, next_


def _build_categories_tree(user, plan=None, filter_empty=False):
    items_by_cat = {}
    if plan:
        for item in plan.items.select_related('category'):
            items_by_cat[item.category_id] = item

    root_cats = Category.objects.filter(
        user=user,
        category_type='EXPENSE',
        is_active=True,
        parent__isnull=True,
    ).prefetch_related('children')

    tree = []
    for parent in root_cats:
        children = [
            {'category': child, 'item': items_by_cat.get(child.pk)}
            for child in parent.children.filter(is_active=True)
        ]
        if filter_empty:
            children = [c for c in children if c['item']]

        parent_item = items_by_cat.get(parent.pk)
        if filter_empty and not parent_item and not children:
            continue

        tree.append({
            'category': parent,
            'item': parent_item,
            'children': children,
        })
    return tree


class PlanningEntryView(LoginRequiredMixin, View):

    def get(self, request):
        today = date.today()
        return redirect('budgets:planning_dashboard', year=today.year, month=today.month)


class PlanningHeaderView(LoginRequiredMixin, View):

    template_name = 'budgets/planning_header.html'

    def get(self, request):
        today = date.today()
        year = int(str(request.GET.get('year', today.year)).replace('.', '').replace(',', ''))
        month = int(str(request.GET.get('month', today.month)).replace('.', '').replace(',', ''))
        form = MonthlyPlanHeaderForm()
        return render(request, self.template_name, {'form': form, 'year': year, 'month': month})

    def post(self, request):
        today = date.today()
        year = int(str(request.POST.get('_year', today.year)).replace('.', '').replace(',', ''))
        month = int(str(request.POST.get('_month', today.month)).replace('.', '').replace(',', ''))

        existing = MonthlyPlan.get_or_none(request.user, year, month)
        form = MonthlyPlanHeaderForm(request.POST, instance=existing)

        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = request.user
            plan.year = year
            plan.month = month
            plan.teto_despesas = plan.teto_calculado
            if not plan.pk:
                plan.status = MonthlyPlan.STATUS_DRAFT
            plan.save()
            return redirect('budgets:planning_distribute', year=year, month=month)

        return render(request, self.template_name, {'form': form, 'year': year, 'month': month})


class PlanningDistributeView(LoginRequiredMixin, View):

    template_name = 'budgets/planning_distribute.html'

    def _get_plan(self, request, year, month):
        return get_object_or_404(
            MonthlyPlan, user=request.user, year=year, month=month
        )

    def get(self, request, year, month):
        plan = self._get_plan(request, year, month)
        tree = _build_categories_tree(request.user, plan)
        context = {
            'plan': plan,
            'categories_tree': tree,
            'teto_calculado': plan.teto_calculado,
        }
        return render(request, self.template_name, context)

    def post(self, request, year, month):
        plan = self._get_plan(request, year, month)

        visible_raw = request.POST.get('visible_categories', '')
        visible_ids = set()
        for v in visible_raw.split(','):
            v = v.strip()
            if v.isdigit():
                visible_ids.add(int(v))
        allocatable_ids = get_allocatable_expense_category_ids(request.user)

        cat_names = dict(
            Category.objects.filter(user=request.user, is_active=True)
            .values_list('pk', 'name')
        )

        submitted_ids = set()
        for key, raw_value in request.POST.items():
            if not key.startswith('amount_'):
                continue
            try:
                cat_id = int(key[len('amount_'):])
            except ValueError:
                continue

            raw_value = raw_value.strip()
            if ',' in raw_value:
                raw_value = raw_value.replace('.', '').replace(',', '.')
            if not raw_value:
                MonthlyPlanItem.objects.filter(
                    monthly_plan=plan, category_id=cat_id
                ).delete()
                submitted_ids.add(cat_id)
                continue

            try:
                amount = Decimal(raw_value)
            except Exception:
                cat_name = cat_names.get(cat_id, f'#{cat_id}')
                messages.error(request, f'Valor inválido para "{cat_name}".')
                continue

            if amount <= Decimal('0'):
                MonthlyPlanItem.objects.filter(
                    monthly_plan=plan, category_id=cat_id
                ).delete()
                submitted_ids.add(cat_id)
                continue

            category = Category.objects.filter(
                pk=cat_id, user=request.user, is_active=True
            ).first()
            if not category:
                continue
            if cat_id not in allocatable_ids:
                continue

            item, _ = MonthlyPlanItem.objects.get_or_create(
                monthly_plan=plan, category=category,
                defaults={'planned_amount': amount},
            )
            if item.planned_amount != amount:
                item.planned_amount = amount
                item.save(update_fields=['planned_amount', 'updated_at'])
            submitted_ids.add(cat_id)

        excluded_ids = visible_ids - submitted_ids
        if excluded_ids:
            MonthlyPlanItem.objects.filter(
                monthly_plan=plan, category_id__in=excluded_ids
            ).delete()

        allocated_total = get_allocated_expense_total(plan)
        if allocated_total > plan.teto_calculado:
            def _fmt(v):
                return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            messages.error(
                request,
                f'A soma das despesas planejadas ({_fmt(allocated_total)}) excede o teto '
                f'calculado ({_fmt(plan.teto_calculado)}).',
            )
            tree = _build_categories_tree(request.user, plan)
            return render(request, self.template_name, {
                'plan': plan,
                'categories_tree': tree,
                'teto_calculado': plan.teto_calculado,
            })

        return redirect('budgets:planning_review', year=year, month=month)


class PlanningReviewView(LoginRequiredMixin, View):

    template_name = 'budgets/planning_review.html'

    def _get_plan(self, request, year, month):
        return get_object_or_404(
            MonthlyPlan, user=request.user, year=year, month=month
        )

    def get(self, request, year, month):
        plan = self._get_plan(request, year, month)
        items = plan.items.select_related('category').order_by('category__name')
        context = {'plan': plan, 'items': items}
        return render(request, self.template_name, context)

    def post(self, request, year, month):
        plan = self._get_plan(request, year, month)
        items = plan.items.select_related('category')

        for item in items:
            key = f'threshold_{item.pk}'
            raw = request.POST.get(key, '').strip()
            if raw:
                try:
                    threshold = int(raw)
                    if 0 <= threshold <= 100:
                        item.alert_threshold = threshold
                        item.save(update_fields=['alert_threshold', 'updated_at'])
                except ValueError:
                    pass
            else:
                item.alert_threshold = None
                item.save(update_fields=['alert_threshold', 'updated_at'])

        plan.status = MonthlyPlan.STATUS_ACTIVE
        plan.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Plano mensal ativado com sucesso.')
        return redirect('budgets:planning_dashboard', year=year, month=month)


class PlanningDashboardView(LoginRequiredMixin, View):

    template_name = 'budgets/planning_dashboard.html'

    def get(self, request, year, month):
        plan = MonthlyPlan.get_or_none(request.user, year, month)
        prev_month, next_month = _adjacent_months(year, month)

        if plan is None:
            previous_plan = (
                MonthlyPlan.objects.filter(user=request.user)
                .exclude(year=year, month__gte=month)
                .filter(year__lte=year)
                .order_by('-year', '-month')
                .first()
            )
            context = {
                'plan': None,
                'prev_month': prev_month,
                'next_month': next_month,
                'year': year,
                'month': month,
                'month_name': MONTH_NAMES_PT[month],
                'has_previous_plan': previous_plan is not None,
            }
            return render(request, self.template_name, context)

        items = plan.items.select_related('category').order_by('category__name')
        alerts = BudgetAlert.objects.unacknowledged_for_user(request.user)
        tree = _build_categories_tree(request.user, plan, filter_empty=True)

        context = {
            'plan': plan,
            'items': items,
            'alerts': alerts,
            'prev_month': prev_month,
            'next_month': next_month,
            'categories_tree': tree,
        }
        return render(request, self.template_name, context)


class PlanningCopyView(LoginRequiredMixin, View):

    def post(self, request, year, month):
        source = (
            MonthlyPlan.objects.filter(user=request.user)
            .exclude(year=year, month=month)
            .order_by('-year', '-month')
            .first()
        )
        if source is None:
            messages.error(request, 'Nenhum plano anterior encontrado para copiar.')
            return redirect('budgets:planning_dashboard', year=year, month=month)

        plan, _ = MonthlyPlan.objects.get_or_create(
            user=request.user,
            year=year,
            month=month,
            defaults={
                'renda_prevista': source.renda_prevista,
                'teto_despesas': source.teto_despesas,
                'savings_goal': source.savings_goal,
                'reserva_dividas': source.reserva_dividas,
                'reserva_metas': source.reserva_metas,
                'reserva_investimentos': source.reserva_investimentos,
                'status': MonthlyPlan.STATUS_DRAFT,
            },
        )

        copy_allocatable_plan_items(source, plan)

        return redirect(
            'budgets:planning_distribute',
            year=year,
            month=month,
        )




class BudgetAlertListView(LoginRequiredMixin, ListView):
    """List all budget alerts for the current user, newest first."""

    model = BudgetAlert
    template_name = 'budgets/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 30

    def get_queryset(self):
        return (
            BudgetAlert.objects
            .filter(user=self.request.user)
            .select_related('budget', 'budget__category')
            .order_by('-triggered_at')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['unread_count'] = BudgetAlert.objects.unacknowledged_for_user(
            self.request.user,
        ).count()
        return ctx


class BudgetAlertAckView(LoginRequiredMixin, View):
    """POST-only endpoint to acknowledge a single alert."""

    def post(self, request, pk):
        alert = get_object_or_404(BudgetAlert, pk=pk, user=request.user)
        alert.acknowledge()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'alert_id': alert.pk})
        messages.success(request, 'Alerta marcado como lido.')
        return redirect('budgets:alerts')


class BudgetAlertAckAllView(LoginRequiredMixin, View):
    """Acknowledge every unread alert in one call."""

    def post(self, request):
        unread = BudgetAlert.objects.unacknowledged_for_user(request.user)
        count = unread.update(acknowledged_at=timezone.now())
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'acknowledged': count})
        messages.success(request, f'{count} alerta(s) marcado(s) como lido(s).')
        return redirect('budgets:alerts')
