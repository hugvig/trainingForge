from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile_view, name='profile'),
    path('training/plan', views.plan_view, name='plan'),
    path('training/exercices', views.excercices_view, name='excercices'),
    path('register', views.register_view, name='register'),
]
