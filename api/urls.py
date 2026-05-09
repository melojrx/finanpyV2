from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    CategoryViewSet,
    MonthlyPlanItemViewSet,
    MonthlyPlanViewSet,
    TransactionViewSet,
    MonthlySummaryView,
    YearlySummaryView,
)

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='api-account')
router.register(r'categories', CategoryViewSet, basename='api-category')
router.register(r'transactions', TransactionViewSet, basename='api-transaction')
router.register(r'monthly-plans', MonthlyPlanViewSet, basename='api-monthly-plan')
router.register(
    r'monthly-plan-items', MonthlyPlanItemViewSet, basename='api-monthly-plan-item'
)

urlpatterns = [
    path('', include(router.urls)),
    path('summary/monthly/', MonthlySummaryView.as_view(), name='api-summary-monthly'),
    path('summary/yearly/', YearlySummaryView.as_view(), name='api-summary-yearly'),
]
