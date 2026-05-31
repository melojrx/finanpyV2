from django import forms
from django.core.exceptions import ValidationError
from .models import Tag


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nome da tag',
                'maxlength': '50',
                'enterkeyhint': 'done',
                'autocapitalize': 'none',
            }),
        }
        labels = {'name': 'Nome da Tag'}

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip().lower()
        if not name:
            raise ValidationError('O nome da tag não pode estar vazio.')

        existing = Tag.objects.filter(user=self.user, name=name)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError(f'Já existe uma tag com o nome "{name}".')

        return name

    def save(self, commit=True):
        tag = super().save(commit=False)
        if self.user and not tag.user_id:
            tag.user = self.user
        if commit:
            tag.save()
        return tag
