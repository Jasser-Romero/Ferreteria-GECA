from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.forms import formset_factory, ModelForm
from django.db import transaction, IntegrityError, models
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, Value, Count
from django.db.models.functions import Coalesce
from datetime import timedelta
from django.utils import timezone

from .models import Cliente, Marca, Categoria, Producto, Venta, VentaDetalle


# Create your views here.
def user_login(request):
    if request.user.is_authenticated:
        # Redirigir según rol
        if request.user.is_superuser:
            return redirect('dashboard')
        else:
            return redirect('productos_lista')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido {username}')

                # REDIRECCIÓN SEGÚN ROL
                if user.is_superuser:
                    return redirect('dashboard')
                else:
                    return redirect('productos_lista')

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
    # Leer mensaje de éxito desde la sesión (y eliminarlo)
    mensaje_exito = request.session.pop('mensaje_exito', None)

    # Eliminar producto (POST)
    if request.method == "POST" and "eliminar_id" in request.POST:
        eliminar_id = request.POST.get("eliminar_id")
        try:
            producto = Producto.objects.get(Id_Producto=eliminar_id)
            producto.delete()
            request.session['mensaje_exito'] = "Producto eliminado correctamente."
        except Producto.DoesNotExist:
            pass

        return redirect("productos_lista")

    # Obtener todos los productos ordenados
    productos = (
        Producto.objects
        .select_related("Marca", "Categoria")
        .order_by("Id_Producto")
    )

    return render(request, "productos.html", {
        "productos": productos,
        "mensaje_exito": mensaje_exito,  # se pasa al template
    })

@login_required
def productos_registrar(request):
    producto = None
    editar_id = request.GET.get("editar")

    if editar_id:
        producto = get_object_or_404(Producto, Id_Producto=editar_id)

    if request.method == "POST":
        nombre = request.POST.get("NombreProducto")
        descripcion = request.POST.get("Descripcion")
        existencia = request.POST.get("Existencia")
        precio = request.POST.get("Precio")
        marca_id = request.POST.get("Marca")
        categoria_id = request.POST.get("Categoria")

        # Validación básica por si acaso (además de la del front)
        if not (nombre and descripcion and existencia and precio and marca_id and categoria_id):
            # NO usamos mensaje_exito / mensaje_error aquí
            return render(request, "productos_registrar.html", {
                "producto": producto,
                "marcas": Marca.objects.filter(Activo=True),
                "categorias": Categoria.objects.filter(Activo=True),
            })

        if producto:
            # Actualizar
            producto.NombreProducto = nombre
            producto.Descripcion = descripcion
            producto.Existencia = existencia
            producto.Precio = precio
            producto.Marca_id = marca_id
            producto.Categoria_id = categoria_id
            producto.save()

            # Guardar mensaje de éxito en sesión
            request.session['mensaje_exito'] = "Producto actualizado correctamente."
        else:
            # Crear
            Producto.objects.create(
                NombreProducto=nombre,
                Descripcion=descripcion,
                Existencia=existencia,
                Precio=precio,
                Marca_id=marca_id,
                Categoria_id=categoria_id,
            )

            request.session['mensaje_exito'] = "Producto creado correctamente."

        # Redirigir SIEMPRE a la lista
        return redirect("productos_lista")

    # GET normal
    return render(request, "productos_registrar.html", {
        "producto": producto,
        "marcas": Marca.objects.filter(Activo=True),
        "categorias": Categoria.objects.filter(Activo=True),
    })


@login_required
def marca_lista(request):
    marcas = Marca.objects.filter(Activo=True).order_by('Id_Marca')
    edit_mode = False
    marca_edit = None
    nombre_valor = ""

    # ELIMINAR (SOFT DELETE: Activo = False)
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        marca = get_object_or_404(Marca, pk=request.POST.get('eliminar_id'))
        marca.Activo = False
        marca.save()
        messages.success(request, 'Marca eliminada correctamente.')
        return redirect('marca_lista')

    # CREAR / ACTUALIZAR
    if request.method == 'POST' and 'eliminar_id' not in request.POST:
        marca_id = request.POST.get('marca_id')
        nombre = request.POST.get('NombreMarca', '').strip()

        if not nombre:
            messages.error(request, 'El nombre de la marca es requerido.')

            if marca_id:
                marca_edit = get_object_or_404(Marca, pk=marca_id)
                edit_mode = True
                nombre_valor = ""  # deja vacío para que el usuario vuelva a escribir
            else:
                nombre_valor = ""  # creación con error
        else:
            if marca_id:
                marca = get_object_or_404(Marca, pk=marca_id)
                marca.NombreMarca = nombre
                marca.save()
                messages.success(request, 'Marca actualizada correctamente.')
            else:
                Marca.objects.create(NombreMarca=nombre, Activo=True)
                messages.success(request, 'Marca registrada correctamente.')
            return redirect('marca_lista')
    else:
        editar_id = request.GET.get('editar')
        if editar_id:
            marca_edit = get_object_or_404(Marca, pk=editar_id)
            edit_mode = True
            nombre_valor = marca_edit.NombreMarca

    context = {
        'marcas': marcas,
        'edit_mode': edit_mode,
        'marca_edit': marca_edit,
        'nombre_valor': nombre_valor,
    }
    return render(request, "marcas.html", context)


@login_required
def categoria_lista(request):
    categorias = Categoria.objects.filter(Activo=True).order_by('Id_Categoria')
    edit_mode = False
    categoria_edit = None
    nombre_valor = ""

    # ELIMINAR (SOFT DELETE: Activo = False)
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        categoria = get_object_or_404(Categoria, pk=request.POST.get('eliminar_id'))
        categoria.Activo = False
        categoria.save()
        messages.success(request, 'Categoría eliminada correctamente.')
        return redirect('categoria_lista')

    # CREAR / ACTUALIZAR
    if request.method == 'POST' and 'eliminar_id' not in request.POST:
        categoria_id = request.POST.get('categoria_id')
        nombre = request.POST.get('NombreCategoria', '').strip()

        if not nombre:
            messages.error(request, 'El nombre de la categoría es requerido.')

            if categoria_id:
                categoria_edit = get_object_or_404(Categoria, pk=categoria_id)
                edit_mode = True
                nombre_valor = ""
            else:
                nombre_valor = ""
        else:
            if categoria_id:
                categoria = get_object_or_404(Categoria, pk=categoria_id)
                categoria.NombreCategoria = nombre
                categoria.save()
                messages.success(request, 'Categoría actualizada correctamente.')
            else:
                Categoria.objects.create(NombreCategoria=nombre, Activo=True)
                messages.success(request, 'Categoría registrada correctamente.')
            return redirect('categoria_lista')
    else:
        editar_id = request.GET.get('editar')
        if editar_id:
            categoria_edit = get_object_or_404(Categoria, pk=editar_id)
            edit_mode = True
            nombre_valor = categoria_edit.NombreCategoria

    context = {
        'categorias': categorias,
        'edit_mode': edit_mode,
        'categoria_edit': categoria_edit,
        'nombre_valor': nombre_valor,
    }
    return render(request, "categorias.html", context)

@login_required
def clientes_lista(request):
    return render(request, "clientes.html")

@login_required
def ventas_lista(request):
    return render(request, "ventas.html")

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['PrimerNombre', 'SegundoNombre', 'PrimerApellido', 'SegundoApellido', 'Activo']
        widgets = {
            'PrimerNombre': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'SegundoNombre': forms.TextInput(attrs={'class': 'form-control'}),
            'PrimerApellido': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'SegundoApellido': forms.TextInput(attrs={'class': 'form-control'}),
            'Activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'PrimerNombre': 'Primer Nombre',
            'SegundoNombre': 'Segundo Nombre',
            'PrimerApellido': 'Primer Apellido',
            'SegundoApellido': 'Segundo Apellido',
            'Activo': 'Activo',
        }

@login_required
def clientes_lista(request):
    clientes = Cliente.objects.all().order_by('Id_Cliente')
    cliente_edit = None
    edit_mode = False

    # ELIMINAR
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        cliente = get_object_or_404(Cliente, pk=request.POST.get('eliminar_id'))
        cliente.delete()
        messages.success(request, 'Cliente eliminado correctamente.')
        return redirect('clientes_lista')

    # CREAR / ACTUALIZAR
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')

        if cliente_id:
            cliente_edit = get_object_or_404(Cliente, pk=cliente_id)
            form = ClienteForm(request.POST, instance=cliente_edit)
            edit_mode = True
        else:
            form = ClienteForm(request.POST)

        if form.is_valid():
            form.save()
            if edit_mode:
                messages.success(request, 'Cliente actualizado correctamente.')
            else:
                messages.success(request, 'Cliente creado correctamente.')
            return redirect('clientes_lista')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        editar_id = request.GET.get('editar')
        if editar_id:
            cliente_edit = get_object_or_404(Cliente, pk=editar_id)
            form = ClienteForm(instance=cliente_edit)
            edit_mode = True
        else:
            form = ClienteForm()

    context = {
        'form': form,
        'clientes': clientes,
        'edit_mode': edit_mode,
        'cliente_edit': cliente_edit,
    }
    return render(request, "clientes.html", context)

@login_required
def clientes_registrar(request):
    cliente_edit = None
    edit_mode = False

    editar_id = request.GET.get('editar')  # Captura si se quiere editar
    if editar_id:
        cliente_edit = get_object_or_404(Cliente, pk=editar_id)
        form = ClienteForm(request.POST or None, instance=cliente_edit)
        edit_mode = True
    else:
        form = ClienteForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            if edit_mode:
                messages.success(request, 'Cliente actualizado correctamente.')
            else:
                messages.success(request, 'Cliente creado correctamente.')
            return redirect('clientes_lista')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')

    context = {
        'form': form,
        'edit_mode': edit_mode,
        'cliente_edit': cliente_edit,
    }
    return render(request, 'clientes_registrar.html', context)

class VentaForm(ModelForm):
    class Meta:
        model = Venta
        fields = ['Cliente']
        widgets = {
            'Cliente': forms.Select(attrs={'class': 'form-select select2'}),
        }



class DetalleVentaForm(ModelForm):
    class Meta:
        model = VentaDetalle
        fields = ['Producto', 'CantidadVendida']
        widgets = {
            'Producto': forms.Select(attrs={'class': 'form-select select2'}),
            'CantidadVendida': forms.NumberInput(attrs={'class': 'form-control'}),
        }

@login_required
def ventas_registrar(request):
    DetalleFormSet = formset_factory(DetalleVentaForm, extra=1)
    clientes = Cliente.objects.filter(Activo=True)
    productos = Producto.objects.all()

    if request.method == "POST":
        venta_form = VentaForm(request.POST)
        detalle_formset = DetalleFormSet(request.POST)

        venta_form.fields["Cliente"].queryset = clientes
        for form in detalle_formset:
            form.fields["Producto"].queryset = productos

        if venta_form.is_valid() and detalle_formset.is_valid():
            detalles_data = []
            for form in detalle_formset:
                if form.cleaned_data:
                    prod = form.cleaned_data["Producto"]
                    qty = form.cleaned_data["CantidadVendida"]
                    if prod.Existencia < qty:
                        messages.error(request, f"No hay stock suficiente para {prod.NombreProducto}. Stock actual: {prod.Existencia}")
                        return render(request, "ventas_registrar.html", {
                            "venta_form": venta_form,
                            "detalle_formset": detalle_formset,
                            "clientes": clientes,
                            "productos": productos,
                        })
                    detalles_data.append((prod, qty))

            try:
                with transaction.atomic():
                    venta = venta_form.save()
                    for prod, qty in detalles_data:
                        detalle = VentaDetalle(
                            Venta=venta,
                            Producto=prod,
                            CantidadVendida=qty,
                            PrecioUnitario=prod.Precio
                        )
                        detalle.save()
                messages.success(request, "Venta registrada correctamente.")
                return redirect("ventas_lista")
            except ValidationError as e:
                messages.error(request, f"Error al registrar la venta: {e}")
                return render(request, "ventas_registrar.html", {
                    "venta_form": venta_form,
                    "detalle_formset": detalle_formset,
                    "clientes": clientes,
                    "productos": productos,
                })
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")

    else:
        venta_form = VentaForm()
        detalle_formset = DetalleFormSet()
        venta_form.fields["Cliente"].queryset = clientes
        for form in detalle_formset:
            form.fields["Producto"].queryset = productos

    return render(request, "ventas_registrar.html", {
        "venta_form": venta_form,
        "detalle_formset": detalle_formset,
        "clientes": clientes,
        "productos": productos,
    })

@login_required
def ventas_lista(request):
    ventas = Venta.objects.select_related('Cliente').annotate(
        total_calculado=Coalesce(
            Sum(F('detalles__CantidadVendida') * F('detalles__PrecioUnitario')),
            Value(0.00),
            output_field=models.DecimalField(max_digits=12, decimal_places=2) 
        )
    ).order_by('-Id_Venta')

    return render(request, "ventas.html", {
        "ventas": ventas
    })

@login_required
def ventas_detalle(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    
    detalles = venta.detalles.select_related('Producto').all()

    return render(request, "ventas_detalle.html", {
        "venta": venta,
        "detalles": detalles
    })

@login_required
def dashboard(request):
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    hace_7_dias = hoy - timedelta(days=7)
    
    # 1. Ventas de Hoy
    ventas_hoy = Venta.objects.filter(Fecha_Venta=hoy).aggregate(total=Sum('Total'))['total'] or 0
    
    # 2. Ventas del Mes
    ventas_mes = Venta.objects.filter(Fecha_Venta__gte=inicio_mes).aggregate(total=Sum('Total'))['total'] or 0
    
    # 3. Productos con Stock Crítico (Menos de 10 unidades)
    productos_bajo_stock = Producto.objects.filter(Existencia__lte=10).count()
    
    # 4. Total de Clientes Activos
    clientes_activos = Cliente.objects.filter(Activo=True).count()

    fechas_grafico = []
    montos_grafico = []

    for i in range(6, -1, -1):
        fecha = hoy - timedelta(days=i)
        venta_dia = Venta.objects.filter(Fecha_Venta=fecha).aggregate(total=Sum('Total'))['total'] or 0
        fechas_grafico.append(fecha.strftime('%d/%m'))
        montos_grafico.append(float(venta_dia))

    top_productos_query = (
        VentaDetalle.objects
        .values('Producto__NombreProducto')
        .annotate(total_vendido=Sum('CantidadVendida'))
        .order_by('-total_vendido')[:5]
    )

    labels_productos = []
    data_productos = []
    
    for item in top_productos_query:
        labels_productos.append(item['Producto__NombreProducto'])
        data_productos.append(item['total_vendido'])

    ultimas_ventas = Venta.objects.select_related('Cliente').order_by('-Id_Venta')[:5]

    context = {
        'ventas_hoy': ventas_hoy,
        'ventas_mes': ventas_mes,
        'productos_bajo_stock': productos_bajo_stock,
        'clientes_activos': clientes_activos,
        'fechas_grafico': fechas_grafico,
        'montos_grafico': montos_grafico,
        'labels_productos': labels_productos,
        'data_productos': data_productos,
        'ultimas_ventas': ultimas_ventas
    }

    return render(request, 'index.html', context)