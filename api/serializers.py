from decimal import Decimal

from rest_framework import serializers

from accounts.models import Account, FundTransfer
from budgets.models import Budget, MonthlyPlan, MonthlyPlanItem
from categories.models import Category
from goals.models import Goal, GoalContribution
from tags.models import Tag
from transactions.models import Transaction


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'id', 'name', 'account_type', 'balance',
            'currency', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']



class FundTransferSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source='from_account.name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.name', read_only=True)

    class Meta:
        model = FundTransfer
        fields = [
            'id', 'from_account', 'from_account_name', 'to_account',
            'to_account_name', 'amount', 'description', 'transfer_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'from_account_name', 'to_account_name',
            'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'transfer_date': {'required': False},
        }

    def validate(self, data):
        from datetime import date as _date

        user = self.context['request'].user
        from_account = data.get('from_account')
        to_account = data.get('to_account')
        if not data.get('transfer_date'):
            data['transfer_date'] = _date.today()

        if from_account and from_account.user != user:
            raise serializers.ValidationError({
                'from_account': 'Conta de origem não pertence ao usuário.'
            })
        if to_account and to_account.user != user:
            raise serializers.ValidationError({
                'to_account': 'Conta de destino não pertence ao usuário.'
            })
        if from_account and to_account and from_account.pk == to_account.pk:
            raise serializers.ValidationError({
                'to_account': 'Conta de destino deve ser diferente da origem.'
            })
        return data

    def create(self, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return FundTransfer.create_and_apply(
                user=self.context['request'].user,
                **validated_data,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'category_type', 'color',
            'icon', 'parent', 'is_active',
        ]
        read_only_fields = ['id']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        """Normalize and check uniqueness per user."""
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError("O nome da tag não pode ser vazio.")
        request = self.context.get('request')
        if request and request.user:
            qs = Tag.objects.filter(user=request.user, name=normalized)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Tag com este nome já existe."
                )
        return normalized


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_full_path = serializers.CharField(source='category.full_path', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False,
        queryset=Tag.objects.all(), source='tags',
    )
    amount_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_type',
            'amount',
            'amount_display',
            'description',
            'transaction_date',
            'status',
            'status_display',
            'confirmed_at',
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
            'tags',
            'tag_ids',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'account_name', 'category_name', 'category_full_path',
            'category_color', 'category_icon', 'amount_display',
            'status_display', 'confirmed_at', 'tags',
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

        tag_ids = data.get('tags', [])
        for tag in tag_ids:
            if tag.user != user:
                raise serializers.ValidationError({'tag_ids': 'Tag não pertence ao usuário.'})

        return data

    @staticmethod
    def _apply_status_defaults(validated_data):
        from django.utils import timezone

        status = validated_data.get('status') or 'CONFIRMED'
        validated_data['status'] = status
        if status == 'CONFIRMED' and not validated_data.get('confirmed_at'):
            validated_data['confirmed_at'] = timezone.now()
            validated_data['auto_confirm'] = False
        elif status == 'PENDING':
            validated_data['confirmed_at'] = None
            validated_data['auto_confirm'] = False
        return validated_data

    def create(self, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError

        tags = validated_data.pop('tags', [])
        try:
            instance = super().create(self._apply_status_defaults(validated_data))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )
        if tags:
            instance.tags.set(tags)
        return instance

    def update(self, instance, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.utils import timezone

        tags = validated_data.pop('tags', None)

        if validated_data.get('status') == 'CONFIRMED' and instance.status != 'CONFIRMED':
            validated_data.setdefault('confirmed_at', timezone.now())
            validated_data['auto_confirm'] = False
        elif validated_data.get('status') == 'PENDING':
            validated_data['confirmed_at'] = None
            validated_data['auto_confirm'] = False

        try:
            instance = super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )
        if tags is not None:
            instance.tags.set(tags)
        return instance


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
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'client_id',
            'transaction_type', 'amount', 'description', 'transaction_date',
            'status', 'status_display', 'confirmed_at',
            'account', 'account_name',
            'category', 'category_name', 'category_full_path',
            'category_color', 'category_icon',
            'amount_display', 'created_at',
        ]
        read_only_fields = [
            'id', 'account_name', 'category_name', 'category_full_path',
            'category_color', 'category_icon', 'amount_display',
            'status_display', 'confirmed_at', 'created_at',
        ]
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'transaction_date': {'required': False},
            'status': {'required': False},
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
            return super().create(
                TransactionSerializer._apply_status_defaults(validated_data)
            )
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


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
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

    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'category', 'category_name', 'category_icon',
            'category_color', 'planned_amount', 'spent_amount',
            'remaining_amount', 'percentage_used', 'is_over_budget',
            'start_date', 'end_date', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'category_name', 'category_icon', 'category_color',
            'spent_amount', 'remaining_amount', 'percentage_used',
            'is_over_budget', 'created_at', 'updated_at',
        ]

    def validate(self, data):
        user = self.context['request'].user
        category = data.get('category')
        if category and category.user != user:
            raise serializers.ValidationError(
                {'category': 'Categoria não pertence ao usuário.'}
            )
        if category and category.category_type != 'EXPENSE':
            raise serializers.ValidationError(
                {'category': 'Orçamentos só podem ser criados para categorias de despesa.'}
            )
        return data

    def create(self, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )

    def update(self, instance, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )


class GoalSerializer(serializers.ModelSerializer):
    progress_pct = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    days_remaining = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id', 'name', 'description', 'target_amount', 'current_amount',
            'deadline', 'icon', 'color', 'status', 'status_display',
            'progress_pct', 'remaining_amount', 'days_remaining',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'current_amount', 'progress_pct', 'remaining_amount',
            'days_remaining', 'status_display', 'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )

    def update(self, instance, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )


class GoalContributionSerializer(serializers.ModelSerializer):
    goal_name = serializers.CharField(source='goal.name', read_only=True)

    class Meta:
        model = GoalContribution
        fields = [
            'id', 'goal', 'goal_name', 'amount', 'date', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'goal_name', 'created_at']

    def validate(self, data):
        user = self.context['request'].user
        goal = data.get('goal')
        if goal and goal.user != user:
            raise serializers.ValidationError(
                {'goal': 'Meta não pertence ao usuário.'}
            )
        if goal and goal.status != Goal.STATUS_ACTIVE:
            raise serializers.ValidationError(
                {'goal': 'Aportes só podem ser feitos em metas ativas.'}
            )
        return data

    def create(self, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )
