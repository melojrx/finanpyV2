from decimal import Decimal

from rest_framework import serializers

from accounts.models import Account
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
