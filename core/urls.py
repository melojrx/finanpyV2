"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token

from core.pwa_views import (
    DeeplinkHandlerView,
    OfflineView,
    manifest,
    service_worker,
)

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),

    # PWA endpoints (servidos na raiz para escopo correto)
    path('sw.js', service_worker, name='service-worker'),
    path('manifest.webmanifest', manifest, name='pwa-manifest'),
    path('offline/', OfflineView.as_view(), name='offline'),
    # Resolver de deeplinks web+finanpy:// (registrado no manifest)
    path('handler/', DeeplinkHandlerView.as_view(), name='deeplink-handler'),

    # Home page
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Authentication and user management URLs
    path('', include('users.urls')),
    
    # Profile management URLs
    path('profile/', include('profiles.urls')),
    
    # Accounts management URLs
    path('accounts/', include('accounts.urls')),
    
    # Categories management URLs
    path('categories/', include('categories.urls')),
    
    # Transactions management URLs
    path('transactions/', include('transactions.urls')),
    
    # Budgets management URLs
    path('budgets/', include('budgets.urls')),

    # Goals management URLs
    path('goals/', include('goals.urls')),

    # REST API
    path('api/v1/', include('api.urls')),
    path('api/token/', obtain_auth_token, name='api-token'),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # django_browser_reload — hot reload de templates/CSS em dev
    urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]
