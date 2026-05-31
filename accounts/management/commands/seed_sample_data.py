"""Seed sample data for testing all features."""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Account
from budgets.models import Budget
from categories.models import Category
from transactions.models import Transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed sample financial data for a given user'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='jrmeloafrf@gmail.com')

    @transaction.atomic
    def handle(self, *args, **options):
        email = options['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stderr.write(f'User {email} not found.')
            return

        self.stdout.write(f'Seeding data for {email}...')

        # Clean existing data
        Transaction.objects.filter(user=user).delete()
        Budget.objects.filter(user=user).delete()
        Category.objects.filter(user=user).delete()
        Account.objects.filter(user=user).delete()

        # --- ACCOUNTS ---
        accounts = {}
        accounts_data = [
            ('Nubank Conta Corrente', 'checking', Decimal('4250.00')),
            ('Itau Poupanca', 'savings', Decimal('12800.00')),
            ('Nubank Credito', 'credit_card', Decimal('-1320.00')),
            ('Carteira', 'cash', Decimal('180.00')),
            ('XP Investimentos', 'investment', Decimal('35000.00')),
        ]
        for name, atype, balance in accounts_data:
            accounts[name] = Account.objects.create(
                user=user, name=name, account_type=atype,
                balance=balance, currency='BRL',
            )
        self.stdout.write(f'  {len(accounts)} contas criadas')

        # --- CATEGORIES (EXPENSE) ---
        expense_cats = {}
        expense_tree = {
            'Moradia': {'icon': '🏠', 'color': '#3B82F6', 'children': [
                'Aluguel', 'Condominio', 'IPTU', 'Manutencao Casa',
            ]},
            'Alimentacao': {'icon': '🍔', 'color': '#10B981', 'children': [
                'Supermercado', 'Restaurantes', 'Delivery', 'Lanches',
            ]},
            'Transporte': {'icon': '🚗', 'color': '#F59E0B', 'children': [
                'Combustivel', 'Uber/99', 'Estacionamento', 'Manutencao Veiculo',
            ]},
            'Saude': {'icon': '🏥', 'color': '#EF4444', 'children': [
                'Plano de Saude', 'Farmacia', 'Consultas', 'Academia',
            ]},
            'Educacao': {'icon': '🎓', 'color': '#8B5CF6', 'children': [
                'Cursos Online', 'Livros', 'Mensalidade',
            ]},
            'Lazer': {'icon': '🎬', 'color': '#EC4899', 'children': [
                'Streaming', 'Cinema', 'Viagens', 'Hobbies',
            ]},
            'Contas Fixas': {'icon': '⚡', 'color': '#06B6D4', 'children': [
                'Energia', 'Agua', 'Internet', 'Celular',
            ]},
            'Compras': {'icon': '🛍️', 'color': '#F97316', 'children': [
                'Roupas', 'Eletronicos', 'Casa e Decoracao',
            ]},
        }

        for parent_name, info in expense_tree.items():
            parent = Category.objects.create(
                user=user, name=parent_name, category_type='EXPENSE',
                icon=info['icon'], color=info['color'],
            )
            expense_cats[parent_name] = parent
            for child_name in info['children']:
                child = Category.objects.create(
                    user=user, name=child_name, category_type='EXPENSE',
                    icon=info['icon'], color=info['color'], parent=parent,
                )
                expense_cats[child_name] = child

        # --- CATEGORIES (INCOME) ---
        income_cats = {}
        income_tree = {
            'Salario': {'icon': '👔', 'color': '#10B981', 'children': []},
            'Freelance': {'icon': '📱', 'color': '#3B82F6', 'children': []},
            'Investimentos': {'icon': '📊', 'color': '#8B5CF6', 'children': [
                'Dividendos', 'Rendimentos',
            ]},
            'Outros Rendimentos': {'icon': '💰', 'color': '#F59E0B', 'children': [
                'Cashback', 'Vendas',
            ]},
        }

        for parent_name, info in income_tree.items():
            parent = Category.objects.create(
                user=user, name=parent_name, category_type='INCOME',
                icon=info['icon'], color=info['color'],
            )
            income_cats[parent_name] = parent
            for child_name in info['children']:
                child = Category.objects.create(
                    user=user, name=child_name, category_type='INCOME',
                    icon=info['icon'], color=info['color'], parent=parent,
                )
                income_cats[child_name] = child

        total_cats = len(expense_cats) + len(income_cats)
        self.stdout.write(f'  {total_cats} categorias criadas')

        # --- TRANSACTIONS ---
        today = date.today()
        transactions_data = []

        # Recurring income - last 3 months
        for months_ago in range(3):
            d = today.replace(day=5) - timedelta(days=30 * months_ago)
            if d > today:
                d = today
            transactions_data.append({
                'type': 'INCOME', 'amount': Decimal('8500.00'),
                'desc': 'Salario mensal', 'cat': 'Salario',
                'account': 'Nubank Conta Corrente', 'date': d,
                'recurring': True, 'recurrence': 'MONTHLY', 'status': 'CONFIRMED',
            })

        # Freelance income
        transactions_data.append({
            'type': 'INCOME', 'amount': Decimal('2200.00'),
            'desc': 'Projeto freelance - landing page', 'cat': 'Freelance',
            'account': 'Nubank Conta Corrente',
            'date': today - timedelta(days=12), 'status': 'CONFIRMED',
        })
        transactions_data.append({
            'type': 'INCOME', 'amount': Decimal('450.00'),
            'desc': 'Dividendos FIIs', 'cat': 'Dividendos',
            'account': 'XP Investimentos',
            'date': today - timedelta(days=8), 'status': 'CONFIRMED',
        })
        transactions_data.append({
            'type': 'INCOME', 'amount': Decimal('89.50'),
            'desc': 'Cashback Nubank', 'cat': 'Cashback',
            'account': 'Nubank Conta Corrente',
            'date': today - timedelta(days=3), 'status': 'CONFIRMED',
        })

        # Fixed expenses - current month
        fixed_expenses = [
            ('Aluguel apartamento', 'Aluguel', Decimal('2200.00'), 10),
            ('Condominio', 'Condominio', Decimal('580.00'), 10),
            ('Plano de saude Unimed', 'Plano de Saude', Decimal('450.00'), 15),
            ('Internet Vivo Fibra', 'Internet', Decimal('119.90'), 8),
            ('Celular Tim', 'Celular', Decimal('69.90'), 12),
            ('Energia eletrica', 'Energia', Decimal('185.00'), 20),
            ('Agua e esgoto', 'Agua', Decimal('95.00'), 18),
            ('Netflix + Spotify', 'Streaming', Decimal('55.90'), 5),
            ('Academia SmartFit', 'Academia', Decimal('99.90'), 1),
        ]
        for desc, cat, amount, day in fixed_expenses:
            d = today.replace(day=min(day, 28))
            if d > today:
                d = d - timedelta(days=30)
            transactions_data.append({
                'type': 'EXPENSE', 'amount': amount, 'desc': desc, 'cat': cat,
                'account': 'Nubank Conta Corrente', 'date': d,
                'recurring': True, 'recurrence': 'MONTHLY', 'status': 'CONFIRMED',
            })

        # Variable expenses - spread over last 45 days
        variable_expenses = [
            ('Supermercado Extra', 'Supermercado', (80, 350)),
            ('iFood', 'Delivery', (25, 75)),
            ('Restaurante almoco', 'Restaurantes', (35, 85)),
            ('Uber para trabalho', 'Uber/99', (15, 45)),
            ('Gasolina', 'Combustivel', (150, 280)),
            ('Farmacia', 'Farmacia', (20, 120)),
            ('Lanche tarde', 'Lanches', (10, 35)),
            ('Estacionamento shopping', 'Estacionamento', (10, 25)),
        ]

        random.seed(42)
        for i in range(40):
            desc, cat, (min_val, max_val) = random.choice(variable_expenses)
            amount = Decimal(str(random.randint(min_val * 100, max_val * 100) / 100))
            d = today - timedelta(days=random.randint(0, 45))
            acc = random.choice(['Nubank Conta Corrente', 'Nubank Credito'])
            status = 'CONFIRMED' if d < today - timedelta(days=2) else 'PENDING'
            transactions_data.append({
                'type': 'EXPENSE', 'amount': amount, 'desc': desc, 'cat': cat,
                'account': acc, 'date': d, 'status': status,
            })

        # Some bigger one-off expenses
        oneoff = [
            ('Curso Alura anual', 'Cursos Online', Decimal('499.00'), 20, 'Nubank Credito'),
            ('Tenis Nike novo', 'Roupas', Decimal('399.90'), 7, 'Nubank Credito'),
            ('Manutencao carro - revisao', 'Manutencao Veiculo', Decimal('850.00'), 25, 'Nubank Conta Corrente'),
            ('Presente aniversario mae', 'Casa e Decoracao', Decimal('189.90'), 14, 'Nubank Credito'),
            ('Cinema + pipoca', 'Cinema', Decimal('78.00'), 3, 'Carteira'),
        ]
        for desc, cat, amount, days_ago, acc in oneoff:
            transactions_data.append({
                'type': 'EXPENSE', 'amount': amount, 'desc': desc, 'cat': cat,
                'account': acc, 'date': today - timedelta(days=days_ago),
                'status': 'CONFIRMED',
            })

        # Future pending transactions
        pending = [
            ('IPTU parcela 6/12', 'IPTU', Decimal('320.00'), -3),
            ('Consulta dentista', 'Consultas', Decimal('250.00'), -5),
        ]
        for desc, cat, amount, days_offset in pending:
            transactions_data.append({
                'type': 'EXPENSE', 'amount': amount, 'desc': desc, 'cat': cat,
                'account': 'Nubank Conta Corrente',
                'date': today - timedelta(days=days_offset),
                'status': 'PENDING', 'auto_confirm': True,
            })

        # Create all transactions
        tx_count = 0
        for tx in transactions_data:
            cat_name = tx['cat']
            cat_obj = expense_cats.get(cat_name) or income_cats.get(cat_name)
            if not cat_obj:
                continue
            Transaction.objects.create(
                user=user,
                account=accounts[tx['account']],
                category=cat_obj,
                transaction_type=tx['type'],
                amount=tx['amount'],
                description=tx['desc'],
                transaction_date=tx['date'],
                status=tx.get('status', 'CONFIRMED'),
                is_recurring=tx.get('recurring', False),
                recurrence_type=tx.get('recurrence') or None,
                auto_confirm=tx.get('auto_confirm', False),
            )
            tx_count += 1

        self.stdout.write(f'  {tx_count} transacoes criadas')

        # --- BUDGETS (current month) ---
        first_day = today.replace(day=1)
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        budgets_data = [
            ('Alimentacao', 'Alimentacao', Decimal('1500.00')),
            ('Transporte', 'Transporte', Decimal('800.00')),
            ('Saude', 'Saude', Decimal('700.00')),
            ('Lazer', 'Lazer', Decimal('400.00')),
            ('Compras', 'Compras', Decimal('600.00')),
            ('Contas Fixas', 'Contas Fixas', Decimal('550.00')),
            ('Educacao', 'Educacao', Decimal('300.00')),
        ]

        budget_count = 0
        for name, cat_name, amount in budgets_data:
            cat_obj = expense_cats.get(cat_name)
            if not cat_obj:
                continue
            Budget.objects.create(
                user=user, category=cat_obj,
                name=f'{name} - {today.strftime("%b/%Y")}',
                planned_amount=amount,
                start_date=first_day, end_date=last_day,
            )
            budget_count += 1

        self.stdout.write(f'  {budget_count} orcamentos criados')
        self.stdout.write(self.style.SUCCESS('Done!'))
