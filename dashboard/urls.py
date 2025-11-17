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
   
    
    path('partial/live/', views.partial_live, name='partial_live'),

    # Bot actions
    path('bots/<int:bot_id>/toggle/', views.toggle_bot, name='toggle_bot'),
    path('bots/<int:bot_id>/edit/', views.bot_edit, name='bot_edit'),

    # Knowledge actions (basic)
     # Partials (HTMX)
    path('partial/knowledge/', views.partial_knowledge, name='partial_knowledge'),

    # Full page (for redirect after edits)
    path('knowledge/', views.knowledge_page, name='knowledge_page'),

    # Knowledge actions
    path('knowledge/add/', views.knowledge_add, name='knowledge_add'),
    path('knowledge/<int:source_id>/edit/', views.knowledge_edit_form, name='knowledge_edit_form'),
    path('knowledge/<int:source_id>/update/', views.knowledge_update, name='knowledge_update'),
    path('knowledge/<int:source_id>/delete/', views.knowledge_delete, name='knowledge_delete'),

    # Chunk actions
    path('knowledge/<int:source_id>/chunks/', views.chunks_list, name='chunks_list'),
    path('knowledge/<int:source_id>/chunks/<int:chunk_id>/edit/', views.chunk_edit_form, name='chunk_edit_form'),
    path('knowledge/<int:source_id>/chunks/<int:chunk_id>/update/', views.chunk_update, name='chunk_update'),
    path('knowledge/<int:source_id>/chunks/<int:chunk_id>/delete/', views.chunk_delete, name='chunk_delete'),
    path('partial/bot_style/', views.partial_bot_style, name='partial_bot_style'),
    path('partial/enquiries/', views.partial_enquiries, name='partial_enquiries'),
    path('bot/<int:bot_id>/style/', views.bot_style_edit, name='bot_style_edit'),
    path('bot/<int:bot_id>/style/save/', views.bot_style_save, name='bot_style_save'),
    
]