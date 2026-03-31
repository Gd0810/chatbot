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
from accounts import views  
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.sitemaps.views import sitemap
from .sitemaps import BotSitemap, StaticViewSitemap

sitemaps = {
    "bots": BotSitemap,
    "static": StaticViewSitemap,
}

def robots_txt(request):
    return HttpResponse(
        f"User-agent: *\nAllow: /\n\nSitemap: https://{request.get_host()}/sitemap.xml",
        content_type="text/plain"
    )


def custom_page_not_found(request, exception):
    return render(request, "404.html", status=404)

urlpatterns = [
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}),
    path("robots.txt", robots_txt),
    path('', views.index, name='index'),
    path('service/', views.services, name='service'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('ai-chatbot-provider-in-vellore/', views.aibot, name='aibot'),
    path('live-chatbot-provider-in-vellore/', views.livebot, name='livebot'),
    path("faq-chatbot-provider-in-vellore/", views.faqbot, name='faqbot'),
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


handler404 = "redbot.urls.custom_page_not_found"
