"""
URL configuration for redbot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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



urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('billing/', include('billing.urls')),
    path('bots/', include('bots.urls')),
    path('knowledge/', include('knowledge.urls')),
    # path('api/chat/', include('chat.urls')),  # DRF API
    path('api/', include('chat.urls')),
    path('embed/', include(('embed.urls', 'embed'), namespace='embed')),
    path('adminpanel/', include('adminpanel.urls')),
    path('dashboard/', include('dashboard.urls')),  # Dashboard as the root
]