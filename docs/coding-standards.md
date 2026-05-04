# Padrões de Código - Finanpy

Este documento define os padrões e convenções de código que devem ser seguidos no desenvolvimento do Finanpy.

## 🐍 Python e Django

### Estilo de Código

- **PEP 8**: Siga rigorosamente as diretrizes do PEP 8
- **Linha máxima**: 88 caracteres (compatível com Black formatter)
- **Indentação**: 4 espaços (nunca tabs)
- **Encoding**: UTF-8 em todos os arquivos Python

### Nomenclatura

```python
# Classes: PascalCase
class UserProfile(models.Model):
    pass

# Funções e métodos: snake_case
def calculate_total_balance():
    pass

# Variáveis: snake_case
user_balance = 0
transaction_date = timezone.now()

# Constantes: UPPER_CASE
MAX_TRANSACTION_AMOUNT = 1000000
DEFAULT_CURRENCY = 'BRL'

# Nomes de arquivos: snake_case.py
user_views.py
transaction_models.py
```

### Models

```python
from django.db import models
from django.utils import timezone

class Transaction(models.Model):
    # Campos obrigatórios primeiro
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE)
    category = models.ForeignKey('categories.Category', on_delete=models.CASCADE)
    
    # Campos principais
    transaction_type = models.CharField(
        max_length=10,
        choices=[('income', 'Receita'), ('expense', 'Despesa')]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200)
    transaction_date = models.DateField()
    
    # Campos opcionais
    notes = models.TextField(blank=True, null=True)
    is_recurring = models.BooleanField(default=False)
    
    # Timestamps sempre por último
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transaction_date', '-created_at']
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
    
    def __str__(self):
        return f"{self.description} - R$ {self.amount}"
    
    def save(self, *args, **kwargs):
        # Lógica personalizada sempre em save()
        super().save(*args, **kwargs)
```

### Views

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy

class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).select_related('account', 'category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_balance'] = self.calculate_balance()
        return context
    
    def calculate_balance(self):
        # Métodos privados no final da classe
        return self.get_queryset().aggregate(
            total=models.Sum('amount')
        )['total'] or 0
```

### Forms

```python
from django import forms
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'account', 'category', 'transaction_type',
            'amount', 'description', 'transaction_date', 'notes'
        ]
        widgets = {
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
            'description': forms.TextInput(attrs={'placeholder': 'Descrição da transação'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['account'].queryset = self.user.account_set.filter(is_active=True)
            self.fields['category'].queryset = self.user.category_set.filter(is_active=True)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return amount
```

## 🗃️ Estrutura de Arquivos

### Apps Django

```
app_name/
├── __init__.py
├── admin.py           # Configurações do Django Admin
├── apps.py           # Configuração do app
├── forms.py          # Formulários
├── models.py         # Modelos de dados
├── urls.py           # URLs do app
├── views.py          # Views e lógica de negócio
├── tests/            # Testes organizados
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   └── test_forms.py
├── templates/        # Templates específicos do app
│   └── app_name/
│       ├── base.html
│       └── model_list.html
├── static/           # Assets estáticos do app
│   └── app_name/
│       ├── css/
│       ├── js/
│       └── img/
└── migrations/       # Migrações do banco
```

### Organização de Imports

```python
# 1. Imports da biblioteca padrão
import json
from datetime import datetime, timedelta

# 2. Imports de terceiros
from django.db import models
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

# 3. Imports locais
from .models import Transaction
from ..accounts.models import Account
from core.utils import format_currency
```

## 🎨 Frontend (Templates e CSS)

### Templates Django

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Finanpy{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {% block extra_css %}{% endblock %}
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <nav class="bg-gray-800 border-b border-gray-700">
        <!-- Navegação -->
    </nav>
    
    <main class="container mx-auto px-4 py-8">
        {% block content %}
        {% endblock %}
    </main>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

```html
<!-- templates/transactions/transaction_list.html -->
{% extends 'base.html' %}

{% block title %}Transações - Finanpy{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <div class="flex justify-between items-center mb-8">
        <h1 class="text-3xl font-bold">Transações</h1>
        <a href="{% url 'transactions:create' %}" 
           class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg transition-colors">
            Nova Transação
        </a>
    </div>
    
    <!-- Filtros -->
    <div class="bg-gray-800 rounded-lg p-6 mb-6">
        <!-- Conteúdo dos filtros -->
    </div>
    
    <!-- Lista de transações -->
    <div class="space-y-4">
        {% for transaction in transactions %}
            <div class="bg-gray-800 rounded-lg p-4 hover:bg-gray-750 transition-colors">
                <!-- Conteúdo da transação -->
            </div>
        {% empty %}
            <div class="text-center py-12">
                <p class="text-gray-400">Nenhuma transação encontrada.</p>
            </div>
        {% endfor %}
    </div>
    
    <!-- Paginação -->
    {% if is_paginated %}
        <div class="mt-8">
            <!-- Links de paginação -->
        </div>
    {% endif %}
</div>
{% endblock %}
```

### TailwindCSS

- **Theme**: Usar tema escuro como padrão
- **Build atual**: TailwindCSS via CDN; arquivos em `static/css/` devem conter
  CSS comum, sem `@apply`.
- **Cores principais**: 
  - Background: `bg-gray-900`, `bg-gray-800`
  - Text: `text-white`, `text-gray-300`
  - Primary: `bg-blue-600`, `hover:bg-blue-700`
  - Success: `bg-green-600`, `text-green-400`
  - Danger: `bg-red-600`, `text-red-400`

```css
/* Classes customizadas quando necessário */
.card {
    background-color: #1f2937;
    border-radius: 0.5rem;
    box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    padding: 1.5rem;
}

.btn-primary {
    background-color: #2563eb;
    color: #fff;
    border-radius: 0.5rem;
    padding: 0.5rem 1rem;
    font-weight: 500;
    transition: background-color 0.2s ease;
}

.form-input {
    background-color: #374151;
    border: 1px solid #4b5563;
    border-radius: 0.5rem;
    color: #fff;
    padding: 0.5rem 0.75rem;
}
```

## 📊 JavaScript

```javascript
// static/js/base.js
document.addEventListener('DOMContentLoaded', function() {
    // Inicialização global
    initializeToasts();
    initializeModals();
});

function initializeToasts() {
    const toasts = document.querySelectorAll('[data-toast]');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.remove();
        }, 5000);
    });
}

// charts.js - Para gráficos
function createBalanceChart(data) {
    const ctx = document.getElementById('balance-chart').getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Saldo',
                data: data.values,
                borderColor: '#3B82F6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#E5E7EB'
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#9CA3AF' },
                    grid: { color: '#374151' }
                },
                y: {
                    ticks: { color: '#9CA3AF' },
                    grid: { color: '#374151' }
                }
            }
        }
    });
}
```

## 🧪 Testes

```python
# tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from ..models import Transaction, Account, Category

User = get_user_model()

class TransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.account = Account.objects.create(
            user=self.user,
            name='Conta Corrente',
            account_type='checking',
            balance=Decimal('1000.00')
        )
        self.category = Category.objects.create(
            user=self.user,
            name='Alimentação',
            category_type='expense'
        )
    
    def test_transaction_creation(self):
        transaction = Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.category,
            transaction_type='expense',
            amount=Decimal('50.00'),
            description='Almoço'
        )
        self.assertEqual(str(transaction), 'Almoço - R$ 50.00')
        self.assertEqual(transaction.user, self.user)
    
    def test_transaction_amount_validation(self):
        with self.assertRaises(ValueError):
            Transaction.objects.create(
                user=self.user,
                account=self.account,
                category=self.category,
                transaction_type='expense',
                amount=Decimal('-50.00'),  # Valor negativo
                description='Teste'
            )
```

## 🔧 Configurações e Variáveis

```python
# settings.py
import os
from pathlib import Path

# Environment variables
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
```

## 📝 Documentação

### Docstrings

```python
def calculate_balance(user, start_date=None, end_date=None):
    """
    Calcula o saldo total de um usuário baseado em suas transações.
    
    Args:
        user (User): Usuário para calcular o saldo
        start_date (date, optional): Data inicial do período
        end_date (date, optional): Data final do período
    
    Returns:
        Decimal: Saldo calculado
    
    Raises:
        ValueError: Se start_date for maior que end_date
    """
    if start_date and end_date and start_date > end_date:
        raise ValueError("Data inicial deve ser menor que data final")
    
    queryset = Transaction.objects.filter(user=user)
    
    if start_date:
        queryset = queryset.filter(transaction_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(transaction_date__lte=end_date)
    
    return queryset.aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
```

### Comentários

```python
# Comentários em português para explicar lógica complexa
def process_recurring_transactions():
    """Processa transações recorrentes pendentes."""
    
    # Busca transações recorrentes que precisam ser processadas
    pending_transactions = Transaction.objects.filter(
        is_recurring=True,
        next_occurrence__lte=timezone.now().date()
    )
    
    for transaction in pending_transactions:
        # Cria nova instância da transação
        new_transaction = Transaction.objects.create(
            user=transaction.user,
            account=transaction.account,
            category=transaction.category,
            # ... outros campos
        )
        
        # Atualiza data da próxima ocorrência
        transaction.calculate_next_occurrence()
        transaction.save()
```

## ✅ Checklist de Code Review

### Antes de fazer commit:
- [ ] Código segue PEP 8
- [ ] Nomes de variáveis e funções são descritivos
- [ ] Não há código comentado desnecessário
- [ ] Imports estão organizados
- [ ] Docstrings estão presentes em funções complexas
- [ ] Testes passam
- [ ] Templates seguem padrão de indentação
- [ ] CSS usa classes TailwindCSS quando possível
- [ ] JavaScript está livre de console.log em produção

### Code Review:
- [ ] Lógica está clara e bem estruturada
- [ ] Não há duplicação de código
- [ ] Validações estão implementadas
- [ ] Tratamento de erros está presente
- [ ] Performance foi considerada
- [ ] Segurança foi considerada
- [ ] Acessibilidade foi considerada (frontend)

---

**Nota**: Estes padrões devem ser seguidos rigorosamente para manter a qualidade e consistência do código. Em caso de dúvidas, consulte a documentação oficial do Django e PEP 8.
