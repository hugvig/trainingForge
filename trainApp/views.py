from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from .forms import RegisterForm

#The home view
def home_view(request):
    return render(request, 'home/home.html')

def login_view(request):
    error_message = ''
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = User.objects.create_user(username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next') or 'home'
            return redirect(next_url)
        else:
            error_message = "INvalid Credentials"
    return render(request, 'accounts/login.html', {'error':error_message}) 

def profile_view(request):
    return render(request, 'profile/profile.html')

def plan_view(request):
    return render(request, 'training/plan.html')

def excercices_view(request):
    return render(request, 'training/exercices.html')
