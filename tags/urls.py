from django.urls import path
from . import views

app_name = 'tags'

urlpatterns = [
    path('', views.TagListView.as_view(), name='list'),
    path('create/', views.TagCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.TagUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.TagDeleteView.as_view(), name='delete'),
]
