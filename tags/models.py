from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Tag(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tags',
    )
    name = models.CharField(max_length=50, verbose_name='Nome')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criada em')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_tag_per_user',
            )
        ]
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        indexes = [
            models.Index(fields=['user', 'name']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip().lower()
        if not self.name:
            raise ValidationError({'name': 'O nome da tag não pode estar vazio.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
