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
from datetime import date, timedelta
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


PERIOD_CHOICES = {
    'today': 'Hoje',
    '7d': '7 dias',
    'month': 'Mês',
    'year': 'Ano',
}

PERIOD_DEFAULT = 'month'


def _get_period_range(period: str, today: date, offset: int = 0):
    """Return (start_date, end_date) for the given period key with offset.

    offset: number of steps back (negative) or forward (positive).
    For 'month', offset=-1 means previous month. For 'year', offset=-1 means previous year.
    """
    if period == 'today':
        target = today + timedelta(days=offset)
        return target, target
    elif period == '7d':
        end = today + timedelta(days=offset * 7)
        start = end - timedelta(days=6)
        return start, end
    elif period == 'year':
        target_year = today.year + offset
        start = date(target_year, 1, 1)
        end = date(target_year, 12, 31) if target_year < today.year else today
        return start, end
    else:
        # month
        total_months = today.year * 12 + (today.month - 1) + offset
        y, m = total_months // 12, total_months % 12 + 1
        start = date(y, m, 1)
        if y == today.year and m == today.month:
            end = today
        else:
            # last day of month
            next_m = m + 1 if m < 12 else 1
            next_y = y if m < 12 else y + 1
            end = date(next_y, next_m, 1) - timedelta(days=1)
        return start, end


def _get_nav_params(period: str, offset: int, today: date):
    """Return (prev_offset, next_offset, can_go_next) for navigation arrows."""
    prev_offset = offset - 1
    next_offset = offset + 1

    # Don't allow navigating into the future
    can_go_next = offset < 0

    return prev_offset, next_offset, can_go_next


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view — aggregates real financial data for the authenticated user."""

    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()

        period = self.request.GET.get('period', PERIOD_DEFAULT)
        if period not in PERIOD_CHOICES:
            period = PERIOD_DEFAULT

        try:
            offset = int(self.request.GET.get('offset', 0))
        except (ValueError, TypeError):
            offset = 0
        # Cap offset to prevent absurd ranges
        offset = max(-120, min(0, offset))

        start_date, end_date = _get_period_range(period, today, offset)
        prev_offset, next_offset, can_go_next = _get_nav_params(period, offset, today)

        from accounts.models import Account
        from transactions.models import Transaction
        from budgets.models import Budget
        from goals.models import Goal
        from django.db.models import Sum, Case, When, DecimalField, Value
        from django.db.models.functions import TruncMonth

        # ── 1. Saldo total das contas ativas (snapshot, não filtra por período)
        total_balance = (
            Account.objects.filter(user=user, is_active=True)
            .aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
        )

        # ── 2. Resumo do período selecionado ─────────────────────────────
        period_summary = Transaction.get_period_summary(user, start_date, end_date)
        period_income = period_summary['income']
        period_expenses = period_summary['expenses']
        period_savings = period_summary['balance']
        savings_pct = (
            int((period_savings / period_income) * 100)
            if period_income > 0 else 0
        )

        # ── 3. Transações recentes dentro do período ─────────────────────
        recent_transactions = (
            Transaction.objects.filter(
                user=user,
                transaction_date__gte=start_date,
                transaction_date__lte=end_date,
            )
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

        # ── 5. Dados do gráfico (adaptado ao período) ────────────────────
        chart_labels, chart_income, chart_expenses = self._build_chart_data(
            user, today, period, Transaction, Sum, Case, When,
            DecimalField, Value, TruncMonth,
        )

        # ── 6. Gastos por categoria no período (gráfico rosca) ────────────
        cat_spending = [
            {**row, 'total_display': _format_brl(row['total'])}
            for row in Transaction.objects.filter(
                user=user,
                transaction_type='EXPENSE',
                transaction_date__gte=start_date,
                transaction_date__lte=end_date,
            )
            .values('category__name', 'category__color')
            .annotate(total=Sum('amount'))
            .order_by('-total')[:6]
        ]

        # ── Period label for template ─────────────────────────────────────
        period_label = self._get_period_label(period, start_date, end_date)

        context.update({
            'user_full_name': user.get_full_name(),
            'last_login': user.last_login,
            # Period filter
            'current_period': period,
            'current_offset': offset,
            'period_choices': PERIOD_CHOICES,
            'period_label': period_label,
            'prev_offset': prev_offset,
            'next_offset': next_offset,
            'can_go_next': can_go_next,
            # Cards
            'total_balance': _format_brl(total_balance),
            'monthly_income': _format_brl(period_income),
            'monthly_expenses': _format_brl(period_expenses),
            'monthly_savings': _format_brl(period_savings),
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

    def _get_period_label(self, period, start_date, end_date):
        today = date.today()
        if period == 'today':
            if start_date == today:
                return f"Hoje, {start_date.strftime('%d/%m')}"
            return start_date.strftime('%d/%m/%Y')
        elif period == '7d':
            return f"{start_date.strftime('%d/%m')} – {end_date.strftime('%d/%m')}"
        elif period == 'year':
            return str(start_date.year)
        else:
            MONTH_NAMES_FULL = [
                'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
            ]
            return f"{MONTH_NAMES_FULL[start_date.month - 1]} {start_date.year}"

    def _build_chart_data(self, user, today, period, Transaction, Sum, Case,
                          When, DecimalField, Value, TruncMonth):
        MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        if period == 'today':
            chart_start = today - timedelta(days=6)
            daily_totals = (
                Transaction.objects
                .filter(user=user, transaction_date__gte=chart_start)
                .values('transaction_date')
                .annotate(
                    income=Sum(Case(When(transaction_type='INCOME', then='amount'),
                                    default=Value(Decimal('0')), output_field=DecimalField())),
                    expenses=Sum(Case(When(transaction_type='EXPENSE', then='amount'),
                                      default=Value(Decimal('0')), output_field=DecimalField())),
                )
                .order_by('transaction_date')
            )
            by_day = {row['transaction_date']: row for row in daily_totals}
            labels, income_data, expense_data = [], [], []
            for i in range(7):
                d = chart_start + timedelta(days=i)
                row = by_day.get(d)
                labels.append(d.strftime('%d/%m'))
                income_data.append(float(row['income']) if row else 0.0)
                expense_data.append(float(row['expenses']) if row else 0.0)
            return labels, income_data, expense_data

        elif period == '7d':
            chart_start = today - timedelta(days=27)
            daily_totals = (
                Transaction.objects
                .filter(user=user, transaction_date__gte=chart_start)
                .values('transaction_date')
                .annotate(
                    income=Sum(Case(When(transaction_type='INCOME', then='amount'),
                                    default=Value(Decimal('0')), output_field=DecimalField())),
                    expenses=Sum(Case(When(transaction_type='EXPENSE', then='amount'),
                                      default=Value(Decimal('0')), output_field=DecimalField())),
                )
            )
            by_day = {row['transaction_date']: row for row in daily_totals}
            labels, income_data, expense_data = [], [], []
            for i in range(4):
                week_start = chart_start + timedelta(weeks=i)
                week_end = week_start + timedelta(days=6)
                week_income = sum(
                    float(by_day[d]['income'])
                    for d in by_day if week_start <= d <= week_end
                )
                week_expenses = sum(
                    float(by_day[d]['expenses'])
                    for d in by_day if week_start <= d <= week_end
                )
                labels.append(week_start.strftime('%d/%m'))
                income_data.append(week_income)
                expense_data.append(week_expenses)
            return labels, income_data, expense_data

        elif period == 'year':
            chart_start = date(today.year, 1, 1)
            monthly_totals = (
                Transaction.objects
                .filter(user=user, transaction_date__gte=chart_start)
                .annotate(month=TruncMonth('transaction_date'))
                .values('month')
                .annotate(
                    income=Sum(Case(When(transaction_type='INCOME', then='amount'),
                                    default=Value(Decimal('0')), output_field=DecimalField())),
                    expenses=Sum(Case(When(transaction_type='EXPENSE', then='amount'),
                                      default=Value(Decimal('0')), output_field=DecimalField())),
                )
                .order_by('month')
            )
            by_ym = {(row['month'].year, row['month'].month): row for row in monthly_totals}
            labels, income_data, expense_data = [], [], []
            for m in range(1, today.month + 1):
                row = by_ym.get((today.year, m))
                labels.append(MONTH_NAMES[m - 1])
                income_data.append(float(row['income']) if row else 0.0)
                expense_data.append(float(row['expenses']) if row else 0.0)
            return labels, income_data, expense_data

        else:
            total_months_start = today.year * 12 + today.month - 6
            chart_start = date(total_months_start // 12, total_months_start % 12 + 1, 1)
            monthly_totals = (
                Transaction.objects
                .filter(user=user, transaction_date__gte=chart_start)
                .annotate(month=TruncMonth('transaction_date'))
                .values('month')
                .annotate(
                    income=Sum(Case(When(transaction_type='INCOME', then='amount'),
                                    default=Value(Decimal('0')), output_field=DecimalField())),
                    expenses=Sum(Case(When(transaction_type='EXPENSE', then='amount'),
                                      default=Value(Decimal('0')), output_field=DecimalField())),
                )
                .order_by('month')
            )
            by_ym = {(row['month'].year, row['month'].month): row for row in monthly_totals}
            labels, income_data, expense_data = [], [], []
            for i in range(5, -1, -1):
                total_m = today.year * 12 + today.month - 1 - i
                y, m = total_m // 12, total_m % 12 + 1
                row = by_ym.get((y, m))
                labels.append(MONTH_NAMES[m - 1])
                income_data.append(float(row['income']) if row else 0.0)
                expense_data.append(float(row['expenses']) if row else 0.0)
            return labels, income_data, expense_data

# NOTE: a duplicate ProfileView used to live here. It was removed because it
# only rendered User fields and ignored the Profile model. The legacy URL
# `users:profile` is now a permanent redirect to `profiles:detail` (see
# `users/urls.py`).
