from django.urls import path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from . import views

app_name = 'embed'

urlpatterns = [
    path('widget/<str:public_key>/', views.widget_iframe, name='widget'),
    path('live/<str:public_key>/', views.live_widget_iframe, name='live_widget'),
    path('config/<str:public_key>/', views.bot_config_api, name='bot_config_api'),
    path('save-enquiry/', views.save_enquiry, name='save_enquiry'),
    path('live/send/', views.live_chat_send, name='live_chat_send'),
    path('live/poll/', views.live_chat_poll, name='live_chat_poll'),
    path('bot.js', lambda request: serve(request, 'embed/bot.js', document_root=settings.STATIC_ROOT or 'static'), name='bot_js'),
    path('live.js', lambda request: serve(request, 'embed/live.js', document_root=settings.STATIC_ROOT or 'static'), name='live_js'),
    path('test/<str:public_key>/', views.test_embed_page, name='test_page_with_bot'),
    path('test/', views.test_embed_page, name='test_page'),
    path('testing/', TemplateView.as_view(template_name='testing/ok.html'), name='test_page'),
    path('livetest/', TemplateView.as_view(template_name='testing/livetest.html'), name='livetest_page'),
    path('qa-test/', TemplateView.as_view(template_name='testing/qa.html'), name='qa_test_page'),
    path('liveqa/', TemplateView.as_view(template_name='testing/liveqa.html'), name='liveqa_test_page'),
    
    # QA Widget
    path('qa/<str:public_key>/', views.qa_widget_iframe, name='qa_widget'),
    path('qa/data/<str:public_key>/', views.qa_data_api, name='qa_data_api'),
]