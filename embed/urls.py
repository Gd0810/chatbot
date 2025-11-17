from django.urls import path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from . import views

urlpatterns = [
    path('widget/<str:public_key>/', views.widget_iframe, name='widget'),
    path('config/<str:public_key>/', views.bot_config_api, name='bot_config_api'),
    path('save-enquiry/', views.save_enquiry, name='save_enquiry'),
    path('bot.js', lambda request: serve(request, 'embed/bot.js', document_root=settings.STATIC_ROOT or 'static'), name='bot_js'),
    path('test/<str:public_key>/', views.test_embed_page, name='test_page_with_bot'),
    path('test/', views.test_embed_page, name='test_page'),
    path('testing/', TemplateView.as_view(template_name='testing/ok.html'), name='test_page'),
]