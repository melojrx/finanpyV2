from django.contrib import admin

from .models import Goal, GoalContribution


class GoalContributionInline(admin.TabularInline):
    model = GoalContribution
    extra = 0
    fields = ('date', 'amount', 'notes', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-date',)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'target_amount',
        'current_amount',
        'status',
        'deadline',
        'created_at',
    )
    list_filter = ('status', 'created_at', 'deadline')
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('current_amount', 'created_at', 'updated_at')
    inlines = (GoalContributionInline,)
    ordering = ('-created_at',)


@admin.register(GoalContribution)
class GoalContributionAdmin(admin.ModelAdmin):
    list_display = ('goal', 'user', 'amount', 'date', 'created_at')
    list_filter = ('date', 'created_at')
    search_fields = ('goal__name', 'user__username', 'user__email', 'notes')
    readonly_fields = ('created_at',)
    ordering = ('-date',)
