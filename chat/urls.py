from django.urls import path
from . import views

urlpatterns = [
   
  path('chat/', views.ChatAPI, name='chat_api'),
]