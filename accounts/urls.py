# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('not-allowed/', views.not_allowed, name='not_allowed'),
    path('password_change/', views.password_change_view, name='password_change'), 
]