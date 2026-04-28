from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

User = get_user_model()


class Goal(models.Model):
    """Financial savings goal owned by a user.

    Progress is tracked through ``GoalContribution`` instances; the cached
    ``current_amount`` is recomputed via signal whenever a contribution is
    created or removed.
    """

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Ativa'),
        (STATUS_COMPLETED, 'Concluída'),
        (STATUS_CANCELLED, 'Cancelada'),
    ]

    ICON_CHOICES = [
        ('🎯', 'Alvo'),
        ('💰', 'Dinheiro'),
        ('🏠', 'Casa'),
        ('🚗', 'Carro'),
        ('✈️', 'Viagem'),
        ('🎓', 'Educação'),
        ('💍', 'Casamento'),
        ('👶', 'Bebê'),
        ('🏥', 'Saúde'),
        ('💻', 'Tecnologia'),
        ('🛡️', 'Reserva de Emergência'),
        ('🎁', 'Presente'),
    ]

    COLOR_CHOICES = [
        ('#3B82F6', 'Azul'),
        ('#10B981', 'Verde'),
        ('#8B5CF6', 'Roxo'),
        ('#F59E0B', 'Amarelo'),
        ('#EF4444', 'Vermelho'),
        ('#06B6D4', 'Ciano'),
        ('#EC4899', 'Rosa'),
        ('#F97316', 'Laranja'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='goals',
        verbose_name='Usuário',
    )
    name = models.CharField(max_length=100, verbose_name='Nome')
    description = models.TextField(blank=True, verbose_name='Descrição')
    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor Alvo',
    )
    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor Atual',
        help_text='Soma dos aportes; atualizado automaticamente.',
    )
    deadline = models.DateField(null=True, blank=True, verbose_name='Prazo')
    icon = models.CharField(
        max_length=10,
        choices=ICON_CHOICES,
        default='🎯',
        verbose_name='Ícone',
    )
    color = models.CharField(
        max_length=7,
        choices=COLOR_CHOICES,
        default='#3B82F6',
        verbose_name='Cor',
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name='Status',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', 'name']
        verbose_name = 'Meta'
        verbose_name_plural = 'Metas'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'deadline']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.name:
            self.name = self.name.strip()
        if not self.name:
            raise ValidationError({'name': 'O nome da meta é obrigatório.'})

        if self.target_amount is not None and self.target_amount <= 0:
            raise ValidationError(
                {'target_amount': 'O valor alvo deve ser maior que zero.'}
            )

        if self.deadline and not self.pk and self.deadline < date.today():
            raise ValidationError(
                {'deadline': 'O prazo não pode ser anterior à data atual.'}
            )

    def get_absolute_url(self):
        return reverse('goals:detail', kwargs={'pk': self.pk})

    @property
    def progress_pct(self):
        """Percentage achieved, capped at 100."""
        if not self.target_amount or self.target_amount <= 0:
            return Decimal('0.00')
        pct = (self.current_amount / self.target_amount) * Decimal('100')
        return min(Decimal('100.00'), round(pct, 2))

    @property
    def remaining_amount(self):
        remaining = self.target_amount - self.current_amount
        return remaining if remaining > 0 else Decimal('0.00')

    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount

    @property
    def days_remaining(self):
        if not self.deadline:
            return None
        return (self.deadline - date.today()).days

    @property
    def status_color_class(self):
        return {
            self.STATUS_ACTIVE: 'text-blue-400',
            self.STATUS_COMPLETED: 'text-green-400',
            self.STATUS_CANCELLED: 'text-gray-400',
        }.get(self.status, 'text-gray-400')


class GoalContribution(models.Model):
    """A single contribution made toward a ``Goal``."""

    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name='contributions',
        verbose_name='Meta',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='goal_contributions',
        verbose_name='Usuário',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor',
    )
    date = models.DateField(verbose_name='Data do Aporte')
    notes = models.TextField(blank=True, verbose_name='Observações')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Aporte'
        verbose_name_plural = 'Aportes'
        indexes = [
            models.Index(fields=['goal', 'date']),
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f'{self.goal.name} — R$ {self.amount} em {self.date}'

    def clean(self):
        super().clean()

        if self.amount is not None and self.amount <= 0:
            raise ValidationError(
                {'amount': 'O valor do aporte deve ser maior que zero.'}
            )

        if self.goal_id and self.user_id and self.goal.user_id != self.user_id:
            raise ValidationError(
                'A meta deve pertencer ao mesmo usuário do aporte.'
            )
