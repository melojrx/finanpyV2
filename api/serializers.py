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
    category_full_path = serializers.CharField(source='category.full_path', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    amount_display = serializers.CharField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_type',
            'amount',
            'amount_display',
            'description',
            'transaction_date',
            'notes',
            'is_recurring',
            'recurrence_type',
            'account',
            'account_name',
            'category',
            'category_name',
            'category_full_path',
            'category_color',
            'category_icon',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'account_name', 'category_name', 'category_full_path',
            'category_color', 'category_icon', 'amount_display',
            'created_at', 'updated_at',
        ]

    def validate(self, data):
        user = self.context['request'].user
        account = data.get('account')
        category = data.get('category')

        if account and account.user != user:
            raise serializers.ValidationError({'account': 'Conta não pertence ao usuário.'})
        if category and category.user != user:
            raise serializers.ValidationError({'category': 'Categoria não pertence ao usuário.'})

        return data


class QuickTransactionSerializer(serializers.ModelSerializer):
    """Serializer otimizado para POST rápido vindo do PWA / Hermes / Background Sync.

    Diferenças do TransactionSerializer padrão:
      - `transaction_date` opcional (default: hoje)
      - `description` opcional (default: nome da categoria escolhida)
      - `notes`, `is_recurring`, `recurrence_type` ignorados (sempre defaults)
      - aceita `client_id` (UUID/string idempotente) para deduplicar requests
        retransmitidas via Background Sync — registrado em `notes` para audit
        até termos campo dedicado.

    O response inclui os mesmos campos read-only enriquecidos do
    TransactionSerializer (amount_display, category_full_path, etc.) para o
    cliente atualizar a UI sem segundo round-trip.
    """

    client_id = serializers.CharField(
        required=False, allow_blank=True, max_length=64, write_only=True,
        help_text='Identificador idempotente do cliente para evitar duplicação.',
    )
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_full_path = serializers.CharField(source='category.full_path', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    amount_display = serializers.CharField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'client_id',
            'transaction_type', 'amount', 'description', 'transaction_date',
            'account', 'account_name',
            'category', 'category_name', 'category_full_path',
            'category_color', 'category_icon',
            'amount_display', 'created_at',
        ]
        read_only_fields = [
            'id', 'account_name', 'category_name', 'category_full_path',
            'category_color', 'category_icon', 'amount_display', 'created_at',
        ]
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'transaction_date': {'required': False},
        }

    def validate(self, data):
        from datetime import date as _date

        user = self.context['request'].user
        account = data.get('account')
        category = data.get('category')

        if account and account.user != user:
            raise serializers.ValidationError({'account': 'Conta não pertence ao usuário.'})
        if category and category.user != user:
            raise serializers.ValidationError({'category': 'Categoria não pertence ao usuário.'})

        # Defaults inteligentes
        if not data.get('transaction_date'):
            data['transaction_date'] = _date.today()
        if not data.get('description', '').strip():
            data['description'] = (category.name if category else 'Transação rápida')[:200]

        # client_id é write-only e não vai para o model
        data.pop('client_id', None)

        return data

    def create(self, validated_data):
        """Captura ValidationError do model (e.g., categoria-tipo) e converte
        em DRF ValidationError (HTTP 400) em vez de propagar como 500."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )


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
