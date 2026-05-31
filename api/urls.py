from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    BudgetViewSet,
    CategoryViewSet,
    DashboardSnapshotView,
    GoalContributionViewSet,
    GoalViewSet,
    MonthlyPlanItemViewSet,
    MonthlyPlanViewSet,
    ReceiptDraftView,
    SyncSinceView,
    TransactionViewSet,
    MonthlySummaryView,
    YearlySummaryView,
)

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='api-account')
router.register(r'categories', CategoryViewSet, basename='api-category')
router.register(r'transactions', TransactionViewSet, basename='api-transaction')
router.register(r'budgets', BudgetViewSet, basename='api-budget')
router.register(r'goals', GoalViewSet, basename='api-goal')
router.register(r'goal-contributions', GoalContributionViewSet, basename='api-goal-contribution')
router.register(r'monthly-plans', MonthlyPlanViewSet, basename='api-monthly-plan')
router.register(
    r'monthly-plan-items', MonthlyPlanItemViewSet, basename='api-monthly-plan-item'
)

urlpatterns = [
    # Paths customizados que conflitam com o router precisam vir ANTES
    # de `include(router.urls)`. Caso contrário, o router casa
    # /transactions/from-receipt/ como /transactions/<pk:from-receipt>/
    # e devolve 405.
    path(
        'transactions/from-receipt/',
        ReceiptDraftView.as_view(),
        name='api-transactions-from-receipt',
    ),
    path('', include(router.urls)),
    path('summary/monthly/', MonthlySummaryView.as_view(), name='api-summary-monthly'),
    path('summary/yearly/', YearlySummaryView.as_view(), name='api-summary-yearly'),
    path('dashboard/snapshot/', DashboardSnapshotView.as_view(), name='api-dashboard-snapshot'),
    path('sync/since/', SyncSinceView.as_view(), name='api-sync-since'),
]
