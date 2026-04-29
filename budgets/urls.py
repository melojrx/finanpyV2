from django.urls import path
from . import views

app_name = 'budgets'

urlpatterns = [
    # Budget CRUD URLs following RESTful patterns
    path('', views.BudgetListView.as_view(), name='list'),
    path('create/', views.BudgetCreateView.as_view(), name='create'),

    # Bulk monthly editor (must come BEFORE the <int:pk> capture below)
    path('monthly/', views.MonthlyBudgetView.as_view(), name='monthly'),
    path(
        'monthly/<int:year>/<int:month>/',
        views.MonthlyBudgetView.as_view(),
        name='monthly_for',
    ),

    path('<int:pk>/', views.BudgetDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.BudgetUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.BudgetDeleteView.as_view(), name='delete'),

    # Budget Alerts
    path('alerts/', views.BudgetAlertListView.as_view(), name='alerts'),
    path('alerts/<int:pk>/ack/', views.BudgetAlertAckView.as_view(), name='alert_ack'),
    path('alerts/ack-all/', views.BudgetAlertAckAllView.as_view(), name='alert_ack_all'),

    # AJAX endpoints for dynamic functionality
    path('api/historical-data/', views.BudgetHistoricalDataView.as_view(), name='historical_data'),
    path('api/<int:pk>/toggle-status/', views.BudgetStatusToggleView.as_view(), name='toggle_status'),
]