from datetime import date
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError

from .models import Goal, GoalContribution


def format_brl_amount(value):
    """Format a Decimal as Brazilian currency without prefix ("1.234,56")."""
    if value is None:
        return ''
    formatted = f'{Decimal(value):,.2f}'
    return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')


def parse_brl_amount(value):
    """Parse a Brazilian-formatted currency string ("1.234,56") to Decimal.

    Also accepts plain ``Decimal``/``float``/``int`` and standard "1234.56".
    Returns ``None`` for empty input.
    """
    if value in (None, '', ' '):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    cleaned = str(value).strip().replace('R$', '').replace(' ', '')
    if not cleaned:
        return None

    if ',' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        raise ValidationError('Informe um valor monetário válido (ex.: 1.234,56).')


class GoalForm(forms.ModelForm):
    target_amount = forms.CharField(
        label='Valor Alvo',
        widget=forms.TextInput(attrs={
            'class': 'form-input currency-mask',
            'inputmode': 'decimal',
            'placeholder': '0,00',
            'autocomplete': 'off',
        }),
    )

    class Meta:
        model = Goal
        fields = ['name', 'description', 'target_amount', 'deadline', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex.: Reserva de Emergência',
                'maxlength': 100,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Detalhes opcionais sobre a meta',
            }),
            'deadline': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'icon': forms.Select(attrs={'class': 'form-input'}),
            'color': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.target_amount is not None:
            self.initial['target_amount'] = format_brl_amount(
                self.instance.target_amount
            )

    def clean_target_amount(self):
        return parse_brl_amount(self.cleaned_data.get('target_amount'))


class GoalContributionForm(forms.ModelForm):
    amount = forms.CharField(
        label='Valor',
        widget=forms.TextInput(attrs={
            'class': 'form-input currency-mask',
            'inputmode': 'decimal',
            'placeholder': '0,00',
            'autocomplete': 'off',
        }),
    )

    class Meta:
        model = GoalContribution
        fields = ['amount', 'date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Observação opcional',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get('date'):
            self.fields['date'].initial = date.today()
        if self.instance.pk and self.instance.amount is not None:
            self.initial['amount'] = format_brl_amount(self.instance.amount)

    def clean_amount(self):
        return parse_brl_amount(self.cleaned_data.get('amount'))
