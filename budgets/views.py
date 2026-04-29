from calendar import monthrange
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Sum, Avg, Count, Case, When, DecimalField, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import json

from .models import Budget, BudgetAlert
from .forms import BudgetForm, BudgetFilterForm, BudgetDeleteConfirmationForm
from categories.models import Category
from transactions.models import Transaction


class BudgetListView(LoginRequiredMixin, ListView):
    """
    List view for budgets with filtering, search, and progress display.
    
    Features:
    - User-scoped budget listing
    - Visual progress bars with color differentiation
    - Filtering by status, category, and date range
    - Search functionality
    - Pagination with performance optimization
    - Summary statistics for dashboard
    """
    
    model = Budget
    template_name = 'budgets/budget_list.html'
    context_object_name = 'budgets'
    paginate_by = 12
    
    def get_queryset(self):
        """Get user-scoped queryset with optimized database queries."""
        queryset = Budget.objects.filter(user=self.request.user).select_related(
            'category'
        ).prefetch_related(
            'category__children'
        ).order_by('-start_date', 'name')
        
        # Apply filters from form
        filter_form = self.get_filter_form()
        if filter_form.is_valid():
            queryset = filter_form.apply_filters(queryset)
            
            # Handle EXCEEDED status filter (requires calculated field)
            if filter_form.cleaned_data.get('status') == 'EXCEEDED':
                # Filter budgets where spending exceeds planned amount
                exceeded_budget_ids = []
                for budget in queryset:
                    if budget.is_over_budget:
                        exceeded_budget_ids.append(budget.id)
                queryset = queryset.filter(id__in=exceeded_budget_ids)
        
        return queryset
    
    def get_filter_form(self):
        """Get initialized filter form with current request data."""
        return BudgetFilterForm(self.request.user, self.request.GET or None)
    
    def get_context_data(self, **kwargs):
        """Add filter form and summary statistics to context."""
        context = super().get_context_data(**kwargs)
        
        # Add filter form
        context['filter_form'] = self.get_filter_form()
        
        # Add budget summary statistics
        context.update(self.get_budget_statistics())
        
        # Add chart data for budget progress visualization
        context['chart_data'] = self.get_chart_data()
        
        # Add current filter parameters for template
        context['current_filters'] = self.request.GET.dict()
        
        return context
    
    def get_budget_statistics(self):
        """
        Calculate comprehensive budget statistics for dashboard display.
        
        Returns:
            dict: Statistics including totals, averages, and status counts
        """
        user_budgets = Budget.objects.filter(user=self.request.user, is_active=True)
        
        if not user_budgets.exists():
            return {
                'stats': {
                    'total_budgets': 0,
                    'total_planned': Decimal('0.00'),
                    'total_spent': Decimal('0.00'),
                    'total_remaining': Decimal('0.00'),
                    'average_usage': Decimal('0.00'),
                    'active_count': 0,
                    'exceeded_count': 0,
                    'completed_count': 0
                }
            }
        
        # Calculate budget statistics
        budgets_list = list(user_budgets)
        total_planned = sum(b.planned_amount for b in budgets_list)
        total_spent = sum(b.spent_amount for b in budgets_list)
        total_remaining = total_planned - total_spent
        
        # Calculate average usage percentage
        usage_percentages = [b.percentage_used for b in budgets_list if b.planned_amount > 0]
        average_usage = sum(usage_percentages) / len(usage_percentages) if usage_percentages else Decimal('0.00')
        
        # Count by status
        active_count = sum(1 for b in budgets_list if b.status == 'ACTIVE')
        exceeded_count = sum(1 for b in budgets_list if b.status == 'EXCEEDED')
        completed_count = sum(1 for b in budgets_list if b.status == 'COMPLETED')
        
        return {
            'stats': {
                'total_budgets': len(budgets_list),
                'total_planned': total_planned,
                'total_spent': total_spent,
                'total_remaining': total_remaining,
                'average_usage': round(average_usage, 2),
                'active_count': active_count,
                'exceeded_count': exceeded_count,
                'completed_count': completed_count
            }
        }
    
    def get_chart_data(self):
        """
        Prepare chart data for budget progress visualization.
        
        Returns:
            dict: Chart data for frontend visualization
        """
        budgets = self.get_queryset()[:6]  # Limit to top 6 for chart display
        
        chart_data = {
            'labels': [],
            'planned': [],
            'spent': [],
            'percentage': []
        }
        
        for budget in budgets:
            chart_data['labels'].append(budget.name[:20])  # Truncate long names
            chart_data['planned'].append(float(budget.planned_amount))
            chart_data['spent'].append(float(budget.spent_amount))
            chart_data['percentage'].append(float(budget.percentage_used))
        
        return json.dumps(chart_data)


class BudgetDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for individual budget with comprehensive analytics.
    
    Features:
    - Budget progress and status information
    - Spending breakdown by subcategories
    - Recent transactions affecting the budget
    - Historical spending trend
    - Time-based progress analysis
    """
    
    model = Budget
    template_name = 'budgets/budget_detail.html'
    context_object_name = 'budget'
    
    def get_queryset(self):
        """Ensure user can only access their own budgets."""
        return Budget.objects.filter(user=self.request.user).select_related('category')
    
    def get_context_data(self, **kwargs):
        """Add comprehensive budget analytics to context."""
        context = super().get_context_data(**kwargs)
        budget = self.object
        
        # Add spending breakdown by subcategories
        context['category_breakdown'] = budget.get_category_breakdown()
        
        # Add recent transactions
        context['recent_transactions'] = budget.get_recent_transactions(limit=10)
        
        # Add spending trend data
        context['spending_trend'] = budget.get_spending_trend(days_back=30)
        
        # Add time progress analytics
        context['time_analytics'] = self.get_time_analytics(budget)
        
        # Add comparison with other budgets
        context['budget_comparison'] = self.get_budget_comparison(budget)
        
        # Prepare chart data for spending visualization
        context['trend_chart_data'] = self.get_trend_chart_data(budget)
        context['breakdown_chart_data'] = self.get_breakdown_chart_data(budget)
        
        return context
    
    def get_time_analytics(self, budget):
        """
        Calculate time-based analytics for budget progress.
        
        Args:
            budget: Budget instance
            
        Returns:
            dict: Time analytics data
        """
        return {
            'days_total': budget.days_total,
            'days_elapsed': budget.days_elapsed,
            'days_remaining': budget.days_remaining,
            'progress_percentage': budget.progress_percentage,
            'is_on_track': budget.percentage_used <= budget.progress_percentage,
            'projected_spending': self.calculate_projected_spending(budget),
            'daily_budget_remaining': self.calculate_daily_budget(budget)
        }
    
    def calculate_projected_spending(self, budget):
        """
        Calculate projected total spending based on current pace.
        
        Args:
            budget: Budget instance
            
        Returns:
            Decimal: Projected total spending
        """
        if budget.days_elapsed <= 0:
            return Decimal('0.00')
        
        daily_average = budget.spent_amount / budget.days_elapsed
        return daily_average * budget.days_total
    
    def calculate_daily_budget(self, budget):
        """
        Calculate daily budget remaining for the rest of the period.
        
        Args:
            budget: Budget instance
            
        Returns:
            Decimal: Daily budget available
        """
        if budget.days_remaining <= 0:
            return Decimal('0.00')
        
        return budget.remaining_amount / budget.days_remaining
    
    def get_budget_comparison(self, budget):
        """
        Compare current budget with similar budgets from previous periods.
        
        Args:
            budget: Budget instance
            
        Returns:
            dict: Comparison data
        """
        # Find similar budgets (same category, similar time periods)
        similar_budgets = Budget.objects.filter(
            user=self.request.user,
            category=budget.category,
            is_active=True
        ).exclude(pk=budget.pk).order_by('-start_date')[:3]
        
        comparisons = []
        for similar_budget in similar_budgets:
            if similar_budget.is_budget_period_past:
                comparisons.append({
                    'name': similar_budget.name,
                    'period': f"{similar_budget.start_date} - {similar_budget.end_date}",
                    'planned_amount': similar_budget.planned_amount,
                    'spent_amount': similar_budget.spent_amount,
                    'percentage_used': similar_budget.percentage_used,
                    'was_successful': not similar_budget.is_over_budget
                })
        
        return comparisons
    
    def get_trend_chart_data(self, budget):
        """
        Prepare spending trend chart data.
        
        Args:
            budget: Budget instance
            
        Returns:
            str: JSON-encoded chart data
        """
        trend_data = budget.get_spending_trend(days_back=30)
        
        chart_data = {
            'labels': [item['transaction_date'].strftime('%d/%m') for item in trend_data],
            'data': [float(item['daily_total']) for item in trend_data]
        }
        
        return json.dumps(chart_data)
    
    def get_breakdown_chart_data(self, budget):
        """
        Prepare category breakdown chart data.
        
        Args:
            budget: Budget instance
            
        Returns:
            str: JSON-encoded chart data
        """
        breakdown = budget.get_category_breakdown()
        
        chart_data = {
            'labels': [item['category_name'] for item in breakdown],
            'data': [float(item['amount_spent']) for item in breakdown]
        }
        
        return json.dumps(chart_data)


class BudgetCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for budgets with historical data preview.
    
    Features:
    - Form with user-scoped category selection
    - Historical spending data for informed planning
    - Validation against overlapping budgets
    - Success message and redirection
    """
    
    model = Budget
    form_class = BudgetForm
    template_name = 'budgets/budget_form.html'
    
    def get_form_kwargs(self):
        """Pass current user to form initialization."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add creation context and helper data."""
        context = super().get_context_data(**kwargs)
        context['action'] = 'create'
        context['title'] = 'Criar Novo Orçamento'
        
        # Add categories for quick selection
        context['categories'] = Category.objects.filter(
            user=self.request.user,
            category_type='EXPENSE',
            is_active=True
        ).order_by('name')
        
        return context
    
    def form_valid(self, form):
        """Handle successful form submission with user assignment."""
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Orçamento "{self.object.name}" criado com sucesso!'
        )
        
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(
            self.request,
            'Erro ao criar orçamento. Verifique os dados e tente novamente.'
        )
        return super().form_invalid(form)
    
    def get_success_url(self):
        """Redirect to budget detail after creation."""
        return reverse('budgets:detail', kwargs={'pk': self.object.pk})


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update view for budgets with validation and change tracking.
    
    Features:
    - User-scoped access control
    - Form validation with current data
    - Change tracking and logging
    - Success feedback
    """
    
    model = Budget
    form_class = BudgetForm
    template_name = 'budgets/budget_form.html'
    
    def get_queryset(self):
        """Ensure user can only edit their own budgets."""
        return Budget.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        """Pass current user to form initialization."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add update context and current budget data."""
        context = super().get_context_data(**kwargs)
        context['action'] = 'update'
        context['title'] = f'Editar Orçamento: {self.object.name}'
        
        # Add current spending and progress info
        context['current_progress'] = {
            'spent_amount': self.object.spent_amount,
            'percentage_used': self.object.percentage_used,
            'remaining_amount': self.object.remaining_amount,
            'status': self.object.status_display
        }
        
        return context
    
    def form_valid(self, form):
        """Handle successful form update with change tracking."""
        # Store old values for comparison
        old_name = self.object.name
        old_planned_amount = self.object.planned_amount
        
        response = super().form_valid(form)
        
        # Create success message with change summary
        changes = []
        if old_name != self.object.name:
            changes.append(f'nome alterado para "{self.object.name}"')
        if old_planned_amount != self.object.planned_amount:
            changes.append(f'valor planejado alterado para {self.object.planned_amount_display}')
        
        if changes:
            change_summary = ', '.join(changes)
            messages.success(
                self.request,
                f'Orçamento atualizado com sucesso: {change_summary}.'
            )
        else:
            messages.success(
                self.request,
                'Orçamento atualizado com sucesso!'
            )
        
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(
            self.request,
            'Erro ao atualizar orçamento. Verifique os dados e tente novamente.'
        )
        return super().form_invalid(form)
    
    def get_success_url(self):
        """Redirect to budget detail after update."""
        return reverse('budgets:detail', kwargs={'pk': self.object.pk})


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete view for budgets with confirmation and safety checks.
    
    Features:
    - User-scoped access control
    - Confirmation form with budget information
    - Safety checks for active budgets
    - Success feedback and redirection
    """
    
    model = Budget
    template_name = 'budgets/budget_confirm_delete.html'
    success_url = reverse_lazy('budgets:list')
    
    def get_queryset(self):
        """Ensure user can only delete their own budgets."""
        return Budget.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add deletion context and budget information."""
        context = super().get_context_data(**kwargs)
        budget = self.object
        
        context['budget_info'] = {
            'has_spending': budget.spent_amount > 0,
            'is_active_period': budget.is_budget_period_active,
            'transaction_count': budget.get_recent_transactions().count(),
            'spent_amount': budget.spent_amount,
            'planned_amount': budget.planned_amount
        }
        
        # Add confirmation form
        context['confirmation_form'] = BudgetDeleteConfirmationForm(budget)
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle deletion with confirmation form validation."""
        self.object = self.get_object()
        confirmation_form = BudgetDeleteConfirmationForm(self.object, request.POST)
        
        if confirmation_form.is_valid():
            return self.delete(request, *args, **kwargs)
        else:
            # Redisplay form with errors
            context = self.get_context_data(confirmation_form=confirmation_form)
            return render(request, self.template_name, context)
    
    def delete(self, request, *args, **kwargs):
        """Perform deletion with success feedback."""
        budget_name = self.object.name
        response = super().delete(request, *args, **kwargs)
        
        messages.success(
            request,
            f'Orçamento "{budget_name}" excluído com sucesso!'
        )
        
        return response


# AJAX Views for Dynamic Functionality

class BudgetHistoricalDataView(LoginRequiredMixin, DetailView):
    """
    AJAX view for retrieving historical spending data for budget planning.
    
    Returns JSON data with spending statistics for the selected category
    to help users make informed budget decisions.
    """
    
    def get(self, request, *args, **kwargs):
        """Return historical data as JSON."""
        category_id = request.GET.get('category_id')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if not all([category_id, start_date_str, end_date_str]):
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        try:
            category = Category.objects.get(
                id=category_id,
                user=request.user,
                category_type='EXPENSE'
            )
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (Category.DoesNotExist, ValueError):
            return JsonResponse({'error': 'Invalid parameters'}, status=400)
        
        # Calculate historical data
        period_days = (end_date - start_date).days + 1
        historical_start = start_date - timedelta(days=365)
        
        transactions = Transaction.objects.filter(
            user=request.user,
            category=category,
            transaction_type='EXPENSE',
            transaction_date__gte=historical_start,
            transaction_date__lt=start_date
        )
        
        if not transactions.exists():
            return JsonResponse({
                'has_data': False,
                'message': 'Nenhum histórico encontrado para esta categoria nos últimos 12 meses.'
            })
        
        stats = transactions.aggregate(
            total_spent=Sum('amount'),
            avg_transaction=Avg('amount'),
            transaction_count=Count('id')
        )
        
        total_days = (start_date - historical_start).days
        daily_avg = stats['total_spent'] / total_days if total_days > 0 else Decimal('0')
        estimated_spending = daily_avg * period_days
        
        return JsonResponse({
            'has_data': True,
            'period_days': period_days,
            'historical_total': float(stats['total_spent']),
            'transaction_count': stats['transaction_count'],
            'daily_average': float(daily_avg),
            'estimated_spending': float(estimated_spending),
            'recommended_budget': float(estimated_spending * Decimal('1.1')),
            'category_name': category.name
        })


class BudgetStatusToggleView(LoginRequiredMixin, DetailView):
    """
    AJAX view for toggling budget active status.
    
    Allows users to quickly activate/deactivate budgets without
    going through the full edit form.
    """
    
    def post(self, request, pk):
        """Toggle budget active status."""
        try:
            budget = Budget.objects.get(pk=pk, user=request.user)
            budget.is_active = not budget.is_active
            budget.save()
            
            return JsonResponse({
                'success': True,
                'new_status': budget.is_active,
                'status_display': 'Ativo' if budget.is_active else 'Inativo',
                'message': f'Orçamento {"ativado" if budget.is_active else "desativado"} com sucesso!'
            })
            
        except Budget.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Orçamento não encontrado.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Erro interno do servidor.'
            }, status=500)


class MonthlyBudgetView(LoginRequiredMixin, View):
    """
    Bulk monthly budget editor.

    Renders all of the user's active EXPENSE categories alongside the
    planned_amount for the selected month. A single POST creates/updates
    every budget at once, instead of forcing the user through CRUD pages
    for each category.

    URL forms:
      - /budgets/monthly/                       -> current month
      - /budgets/monthly/<year>/<month>/        -> arbitrary month

    Behavior:
      - Empty `planned_amount` field deletes the budget for that category/month
        (only if it has no spending recorded yet).
      - Non-empty value upserts the budget (`unique(user, category, start_date)`
        guarantees no duplicates).
      - Read-only metric next to each row: `spent_amount` for the period,
        helping the user calibrate the limit based on real history.
    """

    template_name = 'budgets/monthly_budget.html'

    MIN_PLANNED = Decimal('0.01')

    def _resolve_period(self, year, month):
        if year is None or month is None:
            today = date.today()
            return today.year, today.month

        try:
            year = int(year)
            month = int(month)
            if not (1 <= month <= 12 and 1900 <= year <= 2100):
                raise ValueError
        except (TypeError, ValueError):
            today = date.today()
            return today.year, today.month
        return year, month

    def _period_bounds(self, year, month):
        first = date(year, month, 1)
        last = date(year, month, monthrange(year, month)[1])
        return first, last

    def _build_rows(self, request, year, month, posted=None):
        """
        Build one row per active EXPENSE category for the given month.

        Each row carries: the Category, the existing Budget (if any), the
        current input value (str), the spent_amount for the period, and any
        per-row error message after a failed POST.
        """
        first, last = self._period_bounds(year, month)
        categories = (
            Category.objects.filter(
                user=request.user,
                category_type='EXPENSE',
                is_active=True,
            )
            .select_related('parent')
            .order_by('parent__name', 'name')
        )

        existing = {
            b.category_id: b
            for b in Budget.objects.filter(
                user=request.user, start_date=first, end_date=last,
            ).select_related('category')
        }

        rows = []
        for category in categories:
            budget = existing.get(category.id)
            posted_value = (posted or {}).get(self._field_name(category.id))
            if posted_value is not None:
                value = posted_value.strip()
            elif budget is not None:
                value = f"{budget.planned_amount:.2f}"
            else:
                value = ''
            rows.append({
                'category': category,
                'budget': budget,
                'field_name': self._field_name(category.id),
                'value': value,
                'spent_amount': budget.spent_amount if budget else Decimal('0.00'),
                'error': None,
            })
        return rows

    @staticmethod
    def _field_name(category_id):
        return f'planned_amount_{category_id}'

    def get(self, request, year=None, month=None):
        year, month = self._resolve_period(year, month)
        return self._render(request, year, month, self._build_rows(request, year, month))

    def post(self, request, year=None, month=None):
        year, month = self._resolve_period(year, month)
        first, last = self._period_bounds(year, month)
        rows = self._build_rows(request, year, month, posted=request.POST)

        has_errors = False
        created = updated = removed = 0

        for row in rows:
            raw = row['value']
            category = row['category']
            budget = row['budget']

            if raw == '':
                if budget and budget.spent_amount == 0:
                    budget.delete()
                    removed += 1
                continue

            try:
                amount = Decimal(raw.replace(',', '.'))
            except (InvalidOperation, AttributeError):
                row['error'] = 'Valor inválido.'
                has_errors = True
                continue

            if amount < self.MIN_PLANNED:
                row['error'] = 'O valor planejado deve ser maior que zero.'
                has_errors = True
                continue

            try:
                if budget:
                    if budget.planned_amount != amount:
                        budget.planned_amount = amount
                        budget.save()
                        updated += 1
                else:
                    Budget.objects.create(
                        user=request.user,
                        category=category,
                        name=f'{category.name} - {first.strftime("%m/%Y")}',
                        planned_amount=amount,
                        start_date=first,
                        end_date=last,
                        is_active=True,
                    )
                    created += 1
            except Exception as exc:
                row['error'] = str(exc)
                has_errors = True

        if has_errors:
            messages.error(
                request,
                'Alguns valores não foram salvos. Verifique os destaques abaixo.',
            )
            return self._render(request, year, month, rows)

        parts = []
        if created:
            parts.append(f'{created} criado(s)')
        if updated:
            parts.append(f'{updated} atualizado(s)')
        if removed:
            parts.append(f'{removed} removido(s)')
        if parts:
            messages.success(request, 'Orçamento mensal salvo: ' + ', '.join(parts) + '.')
        else:
            messages.info(request, 'Nenhuma alteração detectada.')

        return redirect('budgets:monthly_for', year=year, month=month)

    def _render(self, request, year, month, rows):
        first, last = self._period_bounds(year, month)
        prev_month = (first - timedelta(days=1))
        next_month = (last + timedelta(days=1))
        context = {
            'year': year,
            'month': month,
            'period_label': first.strftime('%B %Y'),
            'period_start': first,
            'period_end': last,
            'rows': rows,
            'total_planned': sum(
                (Decimal(r['value'].replace(',', '.')) for r in rows
                 if r['value'] and not r['error']),
                Decimal('0.00'),
            ),
            'total_spent': sum(
                (r['spent_amount'] for r in rows), Decimal('0.00'),
            ),
            'prev_year': prev_month.year,
            'prev_month': prev_month.month,
            'next_year': next_month.year,
            'next_month': next_month.month,
        }
        return render(request, self.template_name, context)


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
