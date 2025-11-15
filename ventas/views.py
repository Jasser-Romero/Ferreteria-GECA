from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm


# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido {username}')
                return redirect('index')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos')
        else:
            messages.error(request, 'Datos inválidos')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def user_register(request):
    return render(request, 'register.html')

def user_logout(request):
    logout(request)
    return redirect("login")

@login_required
def productos_lista(request):
    return render(request, "productos.html")

@login_required
def proveedores_lista(request):
    return render(request, "proveedores.html")

@login_required
def clientes_lista(request):
    return render(request, "clientes.html")

@login_required
def ventas_lista(request):
    return render(request, "ventas.html")
