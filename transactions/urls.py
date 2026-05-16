from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    # Main transaction views
    path('', views.TransactionListView.as_view(), name='list'),
    path('create/', views.TransactionCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TransactionDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='delete'),
    path('<int:pk>/confirm/', views.TransactionConfirmView.as_view(), name='confirm'),
    path('<int:pk>/cancel/', views.TransactionCancelView.as_view(), name='cancel'),
    path('bulk-confirm/', views.TransactionBulkConfirmView.as_view(), name='bulk_confirm'),

    # Additional utility views
    path('stats/', views.TransactionStatsView.as_view(), name='stats'),
    
    # AJAX endpoints
    path('api/categories/', views.get_categories_by_type, name='api_categories_by_type'),
    path('api/accounts/', views.get_accounts_data, name='api_accounts_data'),
]