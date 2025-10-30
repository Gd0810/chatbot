from django.urls import path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from . import views

urlpatterns = [
    path('widget/<str:public_key>/', views.widget_iframe, name='widget'),
    # path('test/', views.test_embed, name='test_page'),
    path('bot.js', lambda request: serve(request, 'embed/bot.js', document_root=settings.STATIC_ROOT or 'static'), name='bot_js'),
    path('test/', TemplateView.as_view(template_name='embed/test.html'), name='test_page'),
    path('testing/', TemplateView.as_view(template_name='testing/ok.html'), name='test_page'),  # Add this# Add this
]