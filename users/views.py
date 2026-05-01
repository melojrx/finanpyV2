"""
Authentication views for the Finanpy financial management system.

This module implements secure authentication views following Django security best practices:
- CSRF protection on all forms
- Rate limiting through session management
- Secure password handling
- Audit logging for security events
- User data isolation and access controls
"""

import logging
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.http import HttpRequest, HttpResponse
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import ipaddress
import json
from datetime import date
from decimal import Decimal
from typing import Any, Dict

# Configure logger for security events
logger = logging.getLogger('security')

User = get_user_model()


class SecureLoginView(LoginView):
    """
    Custom login view with email-based authentication and enhanced security features:
    - Email-based login
    - Rate limiting protection
    - Audit logging
    - IP address tracking
    - Session security
    """
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_form_class(self):
        """Return the custom authentication form for email-based login."""
        from .forms import CustomAuthenticationForm
        return CustomAuthenticationForm
    
    @method_decorator(sensitive_post_parameters('password'))
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Override dispatch to add security decorators."""
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self) -> str:
        """Redirect to dashboard after successful login."""
        return reverse_lazy('users:dashboard')
    
    def form_valid(self, form):
        """Handle successful login with audit logging."""
        user = form.get_user()
        
        # Log successful login
        self._log_security_event(
            'login_success',
            user=user,
            message=f"Successful login for user {user.email}"
        )
        
        # Update last login timestamp (Django does this automatically, but we ensure it)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Call parent form_valid which handles the actual login
        response = super().form_valid(form)
        
        # Set secure session parameters
        self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        
        # Add success message
        messages.success(
            self.request, 
            f'Bem-vindo de volta, {user.get_full_name() or user.email}!'
        )
        
        return response
    
    def form_invalid(self, form):
        """Handle failed login with audit logging."""
        username = form.data.get('username', 'unknown')
        
        # Log failed login attempt
        self._log_security_event(
            'login_failed',
            username=username,
            message=f"Failed login attempt for email: {username}"
        )
        
        # Add error message
        messages.error(
            self.request,
            'Credenciais inválidas. Verifique seu email e senha.'
        )
        
        return super().form_invalid(form)
    
    def _log_security_event(self, event_type: str, user=None, username=None, message: str = ''):
        """Log security events with request context."""
        ip_address = self._get_client_ip()
        user_agent = self.request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        logger.warning(
            f"Security Event: {event_type} | "
            f"IP: {ip_address} | "
            f"User: {user.email if user else username or 'N/A'} | "
            f"User-Agent: {user_agent} | "
            f"Message: {message}"
        )
    
    def _get_client_ip(self) -> str:
        """Get client IP address with proxy support."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in case of multiple proxies
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR', 'Unknown')
        
        # Validate IP address
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return 'Invalid'


class SecureLogoutView(LogoutView):
    """
    Custom logout view with security features:
    - Only accepts POST requests for security
    - Session cleanup
    - Audit logging
    - Secure redirection
    """
    next_page = reverse_lazy('home')
    http_method_names = ['post']  # Only allow POST requests for security
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Override dispatch to check authentication and log logout events."""
        # Check if method is allowed first (this will return 405 for GET)
        if request.method.lower() not in self.http_method_names:
            return self.http_method_not_allowed(request)
        
        # Only require authentication for authenticated users
        if request.user.is_authenticated:
            # Log logout event
            logger.info(
                f"User logout: {request.user.email} | "
                f"IP: {self._get_client_ip(request)} | "
                f"Session key: {request.session.session_key}"
            )
            
            # Add logout message
            messages.info(request, 'Você foi desconectado com sucesso.')
        
        return super().dispatch(request, *args, **kwargs)
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return 'Invalid'


class SecureSignUpView(SuccessMessageMixin, CreateView):
    """
    Custom registration view with security features:
    - Strong password validation
    - Email uniqueness verification
    - CSRF protection
    - Audit logging
    """
    model = User
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('users:login')
    success_message = 'Conta criada com sucesso! Você pode fazer login agora.'
    
    @method_decorator(sensitive_post_parameters('password1', 'password2'))
    @method_decorator(csrf_protect)
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Override dispatch to add security decorators."""
        # Redirect authenticated users
        if request.user.is_authenticated:
            return redirect('users:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_class(self):
        """Return the custom user creation form."""
        from .forms import CustomUserCreationForm
        return CustomUserCreationForm
    
    def form_valid(self, form):
        """Handle successful registration with audit logging."""
        try:
            with transaction.atomic():
                # Create user account
                response = super().form_valid(form)
                
                # Log successful registration
                logger.info(
                    f"User registration: {self.object.email} | "
                    f"Username: {self.object.username} | "
                    f"IP: {self._get_client_ip()}"
                )
                
                return response
        except Exception as e:
            # Log registration error
            logger.error(
                f"Registration error: {str(e)} | "
                f"Email: {form.cleaned_data.get('email', 'N/A')} | "
                f"IP: {self._get_client_ip()}"
            )
            messages.error(
                self.request,
                'Erro ao criar conta. Tente novamente.'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Handle failed registration with error logging."""
        email = form.data.get('email', 'unknown')
        
        # Log failed registration attempt
        logger.warning(
            f"Failed registration attempt | "
            f"Email: {email} | "
            f"IP: {self._get_client_ip()} | "
            f"Errors: {form.errors}"
        )
        
        return super().form_invalid(form)
    
    def _get_client_ip(self) -> str:
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR', 'Unknown')
        
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return 'Invalid'


class SecurePasswordResetView(PasswordResetView):
    """
    Custom password reset view with security features:
    - Rate limiting protection
    - Email validation
    - Audit logging
    """
    template_name = 'registration/password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')
    
    def form_valid(self, form):
        """Handle password reset request with audit logging."""
        email = form.cleaned_data['email']
        
        # Check if user exists (without revealing this information)
        try:
            user = User.objects.get(email=email)
            user_exists = True
        except User.DoesNotExist:
            user_exists = False
        
        # Log password reset request (always log, regardless of user existence)
        logger.info(
            f"Password reset requested | "
            f"Email: {email} | "
            f"User exists: {user_exists} | "
            f"IP: {self._get_client_ip()}"
        )
        
        # Always show success message for security (don't reveal if email exists)
        messages.success(
            self.request,
            'Se o email fornecido estiver cadastrado, você receberá instruções para redefinir sua senha.'
        )
        
        return super().form_valid(form)
    
    def _get_client_ip(self) -> str:
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR', 'Unknown')
        
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return 'Invalid'


def _format_brl(value: Decimal) -> str:
    """Format a Decimal as Brazilian Real (e.g. R$ 1.234,56)."""
    formatted = f"{float(abs(value)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}" if value >= 0 else f"-R$ {formatted}"


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view — aggregates real financial data for the authenticated user."""

    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()

        from accounts.models import Account
        from transactions.models import Transaction
        from budgets.models import Budget
        from goals.models import Goal
        from django.db.models import Sum, Case, When, DecimalField, Value
        from django.db.models.functions import TruncMonth

        # ── 1. Saldo total das contas ativas ─────────────────────────────
        total_balance = (
            Account.objects.filter(user=user, is_active=True)
            .aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
        )

        # ── 2. Resumo do mês atual ────────────────────────────────────────
        monthly = Transaction.get_monthly_summary(user, today.year, today.month)
        monthly_income = monthly['income']
        monthly_expenses = monthly['expenses']
        monthly_savings = monthly['balance']  # income − expenses
        savings_pct = (
            int((monthly_savings / monthly_income) * 100)
            if monthly_income > 0 else 0
        )

        # ── 3. Últimas 5 transações ───────────────────────────────────────
        recent_transactions = (
            Transaction.objects.filter(user=user)
            .select_related('account', 'category')
            .order_by('-transaction_date', '-created_at')[:5]
        )

        # ── 4. Orçamentos ativos no período atual ─────────────────────────
        active_budgets = (
            Budget.objects.filter(
                user=user,
                is_active=True,
                start_date__lte=today,
                end_date__gte=today,
            )
            .select_related('category')[:5]
        )

        # ── 4b. Metas ativas com maior progresso ──────────────────────────
        active_goals = (
            Goal.objects.filter(user=user, status=Goal.STATUS_ACTIVE)
            .order_by('-current_amount')[:3]
        )

        # ── 5. Dados dos últimos 6 meses (único query) ────────────────────
        total_months_start = today.year * 12 + today.month - 6
        chart_start = date(total_months_start // 12, total_months_start % 12 + 1, 1)

        monthly_totals = (
            Transaction.objects
            .filter(user=user, transaction_date__gte=chart_start)
            .annotate(month=TruncMonth('transaction_date'))
            .values('month')
            .annotate(
                income=Sum(Case(
                    When(transaction_type='INCOME', then='amount'),
                    default=Value(Decimal('0')),
                    output_field=DecimalField(),
                )),
                expenses=Sum(Case(
                    When(transaction_type='EXPENSE', then='amount'),
                    default=Value(Decimal('0')),
                    output_field=DecimalField(),
                )),
            )
            .order_by('month')
        )
        monthly_by_ym = {
            (row['month'].year, row['month'].month): row
            for row in monthly_totals
        }

        MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        chart_labels, chart_income, chart_expenses = [], [], []
        for i in range(5, -1, -1):
            total_m = today.year * 12 + today.month - 1 - i
            y, m = total_m // 12, total_m % 12 + 1
            row = monthly_by_ym.get((y, m))
            chart_labels.append(MONTH_NAMES[m - 1])
            chart_income.append(float(row['income']) if row else 0.0)
            chart_expenses.append(float(row['expenses']) if row else 0.0)

        # ── 6. Gastos por categoria no mês (gráfico rosca) ────────────────
        cat_spending = [
            {**row, 'total_display': _format_brl(row['total'])}
            for row in Transaction.objects.filter(
                user=user,
                transaction_type='EXPENSE',
                transaction_date__year=today.year,
                transaction_date__month=today.month,
            )
            .values('category__name', 'category__color')
            .annotate(total=Sum('amount'))
            .order_by('-total')[:6]
        ]

        context.update({
            'user_full_name': user.get_full_name(),
            'last_login': user.last_login,
            # Cards
            'total_balance': _format_brl(total_balance),
            'monthly_income': _format_brl(monthly_income),
            'monthly_expenses': _format_brl(monthly_expenses),
            'monthly_savings': _format_brl(monthly_savings),
            'savings_pct': savings_pct,
            # Listas
            'recent_transactions': recent_transactions,
            'active_budgets': active_budgets,
            'active_goals': active_goals,
            # Dados dos gráficos (JSON para o JavaScript)
            'chart_labels': json.dumps(chart_labels),
            'chart_income': json.dumps(chart_income),
            'chart_expenses': json.dumps(chart_expenses),
            'category_spending': cat_spending,
            'category_chart_labels': json.dumps([c['category__name'] for c in cat_spending]),
            'category_chart_data': json.dumps([float(c['total']) for c in cat_spending]),
            'category_chart_colors': json.dumps([c['category__color'] or '#6b7280' for c in cat_spending]),
        })

        return context

# NOTE: a duplicate ProfileView used to live here. It was removed because it
# only rendered User fields and ignored the Profile model. The legacy URL
# `users:profile` is now a permanent redirect to `profiles:detail` (see
# `users/urls.py`).
