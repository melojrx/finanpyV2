from django.urls import path

from . import views

app_name = 'goals'

urlpatterns = [
    path('', views.GoalListView.as_view(), name='list'),
    path('create/', views.GoalCreateView.as_view(), name='create'),
    path('<int:pk>/', views.GoalDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.GoalUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.GoalDeleteView.as_view(), name='delete'),
    path(
        '<int:pk>/contribute/',
        views.GoalContributionCreateView.as_view(),
        name='contribute',
    ),
    path(
        '<int:goal_pk>/contributions/<int:pk>/delete/',
        views.GoalContributionDeleteView.as_view(),
        name='contribution-delete',
    ),
]
