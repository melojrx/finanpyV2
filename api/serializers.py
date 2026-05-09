from decimal import Decimal

from rest_framework import serializers

from accounts.models import Account
from budgets.models import MonthlyPlan, MonthlyPlanItem
from categories.models import Category
from transactions.models import Transaction


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'id', 'name', 'account_type', 'balance',
            'currency', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'category_type', 'color',
            'icon', 'parent', 'is_active',
        ]
        read_only_fields = ['id']


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_type',
            'amount',
            'description',
            'transaction_date',
            'notes',
            'is_recurring',
            'recurrence_type',
            'account',
            'account_name',
            'category',
            'category_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'account_name', 'category_name', 'created_at', 'updated_at']

    def validate(self, data):
        user = self.context['request'].user
        account = data.get('account')
        category = data.get('category')

        if account and account.user != user:
            raise serializers.ValidationError({'account': 'Conta não pertence ao usuário.'})
        if category and category.user != user:
            raise serializers.ValidationError({'category': 'Categoria não pertence ao usuário.'})

        return data


class MonthlyPlanItemSerializer(serializers.ModelSerializer):
    spent_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    percentage_used = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )
    is_over_budget = serializers.BooleanField(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = MonthlyPlanItem
        fields = [
            'id', 'monthly_plan', 'category', 'category_name',
            'planned_amount', 'alert_threshold',
            'spent_amount', 'remaining_amount', 'percentage_used',
            'is_over_budget', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'spent_amount', 'remaining_amount', 'percentage_used',
            'is_over_budget', 'category_name', 'created_at', 'updated_at',
        ]

    def validate(self, data):
        user = self.context['request'].user
        monthly_plan = data.get('monthly_plan')
        category = data.get('category')
        if monthly_plan and monthly_plan.user != user:
            raise serializers.ValidationError(
                {'monthly_plan': 'Plano não pertence ao usuário.'}
            )
        if category and category.user != user:
            raise serializers.ValidationError(
                {'category': 'Categoria não pertence ao usuário.'}
            )
        return data


class MonthlyPlanSerializer(serializers.ModelSerializer):
    renda_realizada = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    despesas_realizadas = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    saldo_disponivel = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    teto_calculado = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    percentual_consumido = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )
    status_display = serializers.CharField(read_only=True)

    class Meta:
        model = MonthlyPlan
        fields = [
            'id', 'year', 'month', 'status', 'status_display',
            'renda_prevista', 'savings_goal', 'teto_despesas', 'teto_calculado',
            'reserva_dividas', 'reserva_metas', 'reserva_investimentos',
            'renda_realizada', 'despesas_realizadas', 'saldo_disponivel',
            'percentual_consumido', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'renda_realizada', 'despesas_realizadas', 'saldo_disponivel',
            'teto_calculado', 'percentual_consumido', 'status_display',
            'created_at', 'updated_at',
        ]


class MonthlyPlanSummarySerializer(MonthlyPlanSerializer):
    """Plano com itens aninhados — usado no endpoint /summary/."""

    items = MonthlyPlanItemSerializer(many=True, read_only=True)

    class Meta(MonthlyPlanSerializer.Meta):
        fields = MonthlyPlanSerializer.Meta.fields + ['items']
