from django.urls import path
from . import views

urlpatterns = [
    path('<int:bot_id>/', views.list, name='list'),
    path('<int:bot_id>/add/', views.add_knowledge, name='add'),
    path('<int:bot_id>/source/<int:source_id>/', views.detail, name='detail'),
]# Add views later