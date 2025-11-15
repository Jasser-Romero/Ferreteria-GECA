from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django import forms

from .models import Proveedor


# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido {username}')
                return redirect('dashboard')
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

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['NombreEmpresa', 'Telefono']
        widgets = {
            'NombreEmpresa': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'Telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '8',
                'required': True
            }),
        }
        labels = {
            'NombreEmpresa': 'Nombre de la empresa',
            'Telefono': 'Teléfono',
        }


@login_required
def proveedores_lista(request):
    proveedores = Proveedor.objects.all().order_by('Id_Proveedor')
    proveedor_edit = None
    edit_mode = False

    # ELIMINAR
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        proveedor = get_object_or_404(Proveedor, pk=request.POST.get('eliminar_id'))
        proveedor.delete()
        messages.success(request, 'Proveedor eliminado correctamente.')
        return redirect('proveedores_lista')

    # CREAR / ACTUALIZAR
    if request.method == 'POST':
        proveedor_id = request.POST.get('proveedor_id')

        if proveedor_id:
            proveedor_edit = get_object_or_404(Proveedor, pk=proveedor_id)
            form = ProveedorForm(request.POST, instance=proveedor_edit)
            edit_mode = True
        else:
            form = ProveedorForm(request.POST)

        if form.is_valid():
            form.save()
            if edit_mode:
                messages.success(request, 'Proveedor actualizado correctamente.')
            else:
                messages.success(request, 'Proveedor creado correctamente.')
            return redirect('proveedores_lista')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        editar_id = request.GET.get('editar')
        if editar_id:
            proveedor_edit = get_object_or_404(Proveedor, pk=editar_id)
            form = ProveedorForm(instance=proveedor_edit)
            edit_mode = True
        else:
            form = ProveedorForm()

    context = {
        'form': form,
        'proveedores': proveedores,
        'edit_mode': edit_mode,
        'proveedor_edit': proveedor_edit,
    }
    return render(request, "proveedores.html", context)

@login_required
def clientes_lista(request):
    return render(request, "clientes.html")

@login_required
def ventas_lista(request):
    return render(request, "ventas.html")
