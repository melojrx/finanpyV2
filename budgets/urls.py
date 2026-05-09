from django.urls import path
from . import views

app_name = 'budgets'

urlpatterns = [
    # Wizard de planejamento mensal
    path('plano/', views.PlanningEntryView.as_view(), name='planning_entry'),
    path('plano/novo/', views.PlanningHeaderView.as_view(), name='planning_header'),
    path(
        'plano/<int:year>/<int:month>/distribuir/',
        views.PlanningDistributeView.as_view(),
        name='planning_distribute',
    ),
    path(
        'plano/<int:year>/<int:month>/revisar/',
        views.PlanningReviewView.as_view(),
        name='planning_review',
    ),
    path(
        'plano/<int:year>/<int:month>/',
        views.PlanningDashboardView.as_view(),
        name='planning_dashboard',
    ),
    path(
        'plano/<int:year>/<int:month>/copiar/',
        views.PlanningCopyView.as_view(),
        name='planning_copy',
    ),

    # Alertas de orçamento
    path('alerts/', views.BudgetAlertListView.as_view(), name='alerts'),
    path('alerts/<int:pk>/ack/', views.BudgetAlertAckView.as_view(), name='alert_ack'),
    path('alerts/ack-all/', views.BudgetAlertAckAllView.as_view(), name='alert_ack_all'),
]