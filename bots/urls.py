from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.bot_list, name='bot_list'),
    path('create/', views.create_bot, name='create'),
    path('<int:bot_id>/edit/', views.edit, name='edit'),
]