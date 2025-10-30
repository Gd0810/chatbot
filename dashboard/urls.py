# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),

    # Partials (HTMX)
    path('partial/account/', views.partial_account, name='partial_account'),
    path('partial/plan/', views.partial_plan, name='partial_plan'),
    path('partial/bots/', views.partial_bots, name='partial_bots'),
    path('partial/knowledge/', views.partial_knowledge, name='partial_knowledge'),
    path('partial/live/', views.partial_live, name='partial_live'),

    # Bot actions
    path('bots/<int:bot_id>/toggle/', views.toggle_bot, name='toggle_bot'),
    path('bots/<int:bot_id>/edit/', views.bot_edit, name='bot_edit'),

    # Knowledge actions (basic)
    path('knowledge/add/', views.knowledge_add, name='knowledge_add'),
    path('knowledge/<int:source_id>/edit/', views.knowledge_edit, name='knowledge_edit'),
]