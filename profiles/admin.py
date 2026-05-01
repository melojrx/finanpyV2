from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin configuration for Profile.

    Names are owned by the related User model — see profile.user.first_name.
    """

    list_display = ['user', 'phone_display', 'birth_date', 'updated_at']
    list_filter = ['created_at', 'updated_at', 'birth_date']
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__username',
        'user__email',
        'phone',
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Usuário', {'fields': ('user',)}),
        ('Pessoal', {'fields': ('phone', 'birth_date')}),
        ('Biografia', {'fields': ('bio',), 'classes': ('wide',)}),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def phone_display(self, obj):
        return obj.phone_display

    phone_display.short_description = 'Telefone'
