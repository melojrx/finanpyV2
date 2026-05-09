from decimal import Decimal

from django.db.models import Sum, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from budgets.models import MonthlyPlan, MonthlyPlanItem
from categories.models import Category
from transactions.models import Transaction

from .serializers import (
    AccountSerializer,
    CategorySerializer,
    MonthlyPlanItemSerializer,
    MonthlyPlanSerializer,
    MonthlyPlanSummarySerializer,
    TransactionSerializer,
)


class AccountViewSet(viewsets.ModelViewSet):
    """CRUD de contas do usuário autenticado."""
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD de categorias do usuário autenticado."""
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(user=self.request.user, is_active=True)
        category_type = self.request.query_params.get('type')
        if category_type in ('INCOME', 'EXPENSE'):
            qs = qs.filter(category_type=category_type)
        return qs.order_by('category_type', 'name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    """CRUD de transações do usuário autenticado."""
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user).select_related(
            'account', 'category'
        )
        params = self.request.query_params

        transaction_type = params.get('type')
        if transaction_type in ('INCOME', 'EXPENSE'):
            qs = qs.filter(transaction_type=transaction_type)

        year = params.get('year')
        month = params.get('month')
        if year:
            qs = qs.filter(transaction_date__year=int(year))
        if month:
            qs = qs.filter(transaction_date__month=int(month))

        account_id = params.get('account')
        if account_id:
            qs = qs.filter(account_id=account_id)

        category_id = params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        return qs.order_by('-transaction_date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MonthlySummaryView(APIView):
    """Resumo financeiro mensal: receitas, despesas, saldo e contagem."""

    def get(self, request):
        try:
            year = int(request.query_params.get('year', 0))
            month = int(request.query_params.get('month', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'year e month devem ser inteiros.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (year and month):
            return Response(
                {'error': 'Parâmetros year e month são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        summary = Transaction.get_monthly_summary(request.user, year, month)

        return Response({
            'year': year,
            'month': month,
            'income': str(summary['income']),
            'expenses': str(summary['expenses']),
            'balance': str(summary['balance']),
            'transaction_count': summary['transaction_count'],
        })


class YearlySummaryView(APIView):
    """Resumo financeiro anual: receitas e despesas por mês."""

    def get(self, request):
        try:
            year = int(request.query_params.get('year', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'year deve ser inteiro.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not year:
            return Response(
                {'error': 'Parâmetro year é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        months = []
        for m in range(1, 13):
            s = Transaction.get_monthly_summary(request.user, year, m)
            months.append({
                'month': m,
                'income': str(s['income']),
                'expenses': str(s['expenses']),
                'balance': str(s['balance']),
                'transaction_count': s['transaction_count'],
            })

        totals = Transaction.objects.filter(
            user=request.user,
            transaction_date__year=year,
        ).aggregate(
            total_income=Sum('amount', filter=Q(transaction_type='INCOME')),
            total_expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        )
        total_income = totals['total_income'] or Decimal('0.00')
        total_expenses = totals['total_expenses'] or Decimal('0.00')

        return Response({
            'year': year,
            'total_income': str(total_income),
            'total_expenses': str(total_expenses),
            'total_balance': str(total_income - total_expenses),
            'months': months,
        })


class MonthlyPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MonthlyPlanSerializer

    def get_queryset(self):
        return MonthlyPlan.objects.filter(
            user=self.request.user
        ).order_by('-year', '-month')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        plan = self.get_object()
        if plan.status != MonthlyPlan.STATUS_DRAFT:
            return Response(
                {'detail': 'Apenas planos em rascunho podem ser ativados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        MonthlyPlan.objects.filter(pk=plan.pk).update(status=MonthlyPlan.STATUS_ACTIVE)
        plan.refresh_from_db()
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=['post'])
    def copy_from_previous(self, request, pk=None):
        plan = self.get_object()
        previous = (
            MonthlyPlan.objects.filter(user=request.user)
            .exclude(pk=plan.pk)
            .filter(
                Q(year__lt=plan.year)
                | Q(year=plan.year, month__lt=plan.month)
            )
            .order_by('-year', '-month')
            .first()
        )
        if not previous:
            return Response(
                {'detail': 'Nenhum plano anterior encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        copied = 0
        for item in previous.items.all():
            _, created = MonthlyPlanItem.objects.get_or_create(
                monthly_plan=plan,
                category=item.category,
                defaults={
                    'planned_amount': item.planned_amount,
                    'alert_threshold': item.alert_threshold,
                },
            )
            if created:
                copied += 1
        return Response({'copied_items': copied, 'plan': self.get_serializer(plan).data})

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        plan = self.get_object()
        return Response(
            MonthlyPlanSummarySerializer(plan, context={'request': request}).data
        )


class MonthlyPlanItemViewSet(viewsets.ModelViewSet):
    serializer_class = MonthlyPlanItemSerializer

    def get_queryset(self):
        qs = MonthlyPlanItem.objects.filter(
            monthly_plan__user=self.request.user
        ).select_related('category', 'monthly_plan')
        monthly_plan_id = self.request.query_params.get('monthly_plan')
        if monthly_plan_id:
            qs = qs.filter(monthly_plan_id=monthly_plan_id)
        return qs

    def perform_create(self, serializer):
        serializer.save()
