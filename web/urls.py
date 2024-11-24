"""web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.urls import path, include
from django.contrib import admin
from predictapp import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('predictapp.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('instruction/', views.instruction, name='instruction'),
    path('contact/', views.contact, name='contact'),
    path('terms_service/', views.terms_service, name='terms_service'),
    path('privacy_policy/', views.privacy_policy, name='privacy_policy'),
    path('trading/', views.trading, name='trading')

    # path('ads/', include('ads.urls')),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

