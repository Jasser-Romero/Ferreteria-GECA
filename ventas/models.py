from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum, Q, CheckConstraint, UniqueConstraint, F
from django.core.exceptions import ValidationError

# Librerias para Manejo de Usuarios
from django.contrib.auth.models import AbstractUser, Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.conf import settings

# Create your models here.
class Cliente(models.Model):
    Id_Cliente=models.AutoField(primary_key=True)
    PrimerNombre=models.CharField(max_length=50)
    SegundoNombre=models.CharField(max_length=50)
    PrimerApellido=models.CharField(max_length=50)
    SegundoApellido=models.CharField(max_length=50)
    Activo=models.BooleanField(default=True)

    def __str__(self):
        return f"{self.PrimerNombre} {self.PrimerApellido}".strip()

class Marca(models.Model):
    Id_Marca=models.AutoField(primary_key=True)
    NombreMarca=models.CharField(max_length=50)
    Activo=models.BooleanField(default=True)

class Categoria(models.Model):
    Id_Categoria=models.AutoField(primary_key=True)
    NombreCategoria=models.CharField(max_length=50)
    Activo=models.BooleanField(default=True)

class Producto(models.Model):
    Id_Producto=models.AutoField(primary_key=True)
    NombreProducto=models.CharField(max_length=50)
    Descripcion=models.CharField(max_length=200)
    Existencia=models.IntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(99999)
        ])
    Precio=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    Marca = models.ForeignKey(Marca, on_delete=models.PROTECT, null=False, blank=False)
    Categoria=models.ForeignKey(Categoria, on_delete=models.PROTECT, null=False, blank=False)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(Existencia__gte=0), name='producto_existencia_ge_0'),
        ]
    
    def __str__(self):
        return self.NombreProducto

class Venta(models.Model):
    Id_Venta=models.AutoField(primary_key=True)
    Fecha_Venta=models.DateField(default=timezone.now)
    Cliente=models.ForeignKey(Cliente,on_delete=models.PROTECT, null=False, blank=False)
    Total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])

    class Meta:
        constraints = [
            CheckConstraint(check=Q(Total__gte=0), name='venta_total_ge_0'),
        ]
        ordering = ['-Fecha_Venta', '-Id_Venta']

    def __str__(self):
        return f"Venta #{self.Id_Venta} ({self.Fecha_Venta})"
    
    def recalcular_total(self, save=True):
        suma = self.detalles.aggregate(s=Sum('SubTotal'))['s'] or Decimal('0.00')
        self.Total = suma
        if save:
            self.save(update_fields=['Total'])

class VentaDetalle(models.Model):
    Venta=models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    Producto=models.ForeignKey('Producto', on_delete=models.PROTECT, related_name='detalles_venta')
    CantidadVendida=models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999999)])
    PrecioUnitario = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    SubTotal=models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        # todo: esta linea de codigo es para evitar que se repita el mismo producto 2 veces en la misma venta
        constraints = [
            UniqueConstraint(fields=['Venta', 'Producto'], name='venta_producto_unico'),
            CheckConstraint(check=Q(CantidadVendida__gte=1), name='cantidad_ge_1'),
             CheckConstraint(check=Q(PrecioUnitario__gte=0), name='precio_unitario_ge_0'),
            CheckConstraint(check=Q(SubTotal__gte=0), name='detalle_subtotal_ge_0'),
        ]

    def __str__(self):
        return f"{self.Producto} x {self.CantidadVendida}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.PrecioUnitario is None:
            self.PrecioUnitario = self.Producto.Precio
        self.SubTotal = (Decimal(self.CantidadVendida) * self.PrecioUnitario).quantize(Decimal('0.01'))

        old = None
        if self.pk:
            old = type(self).objects.select_related('Producto').get(pk=self.pk)

        super().save(*args, **kwargs)

        if old is None:
            prod = Producto.objects.select_for_update().get(pk=self.Producto_id)
            if (prod.Existencia or 0) - self.CantidadVendida < 0:
                raise ValidationError("No hay stock suficiente para realizar la venta.")
            Producto.objects.filter(pk=prod.pk).update(Existencia=F('Existencia') - self.CantidadVendida)
        else:
            if old.Producto_id != self.Producto_id:
                prod_old = Producto.objects.select_for_update().get(pk=old.Producto_id)
                Producto.objects.filter(pk=prod_old.pk).update(Existencia=F('Existencia') + old.CantidadVendida)

                prod_new = Producto.objects.select_for_update().get(pk=self.Producto_id)
                if (prod_new.Existencia or 0) - self.CantidadVendida < 0:
                    raise ValidationError("No hay stock suficiente para cambiar el producto en la venta.")
                Producto.objects.filter(pk=prod_new.pk).update(Existencia=F('Existencia') - self.CantidadVendida)
            else:
                delta = self.CantidadVendida - old.CantidadVendida
                if delta != 0:
                    prod = Producto.objects.select_for_update().get(pk=self.Producto_id)
                    if delta > 0 and (prod.Existencia or 0) - delta < 0:
                        raise ValidationError("No hay stock suficiente para aumentar la cantidad vendida.")
                    Producto.objects.filter(pk=prod.pk).update(Existencia=F('Existencia') - delta)

        self.Venta.recalcular_total(save=True)

# Manejo de Usuarios en el Sistema (solo sección de usuarios modificada)
class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('vendedor', 'Vendedor'),
    ]
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='vendedor')

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"


class TemplateResource(models.Model):
    """Representa un recurso/plantilla al que se puede dar acceso por grupo o usuario.

    - codename: identificador único
    - nombre: etiqueta legible
    - groups: grupos que tienen acceso
    - users: excepciones de usuarios con acceso directo
    """
    codename = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    groups = models.ManyToManyField(Group, blank=True, related_name='template_resources')
    users = models.ManyToManyField('Usuario', blank=True, related_name='template_resources')

    def __str__(self):
        return f"{self.nombre} ({self.codename})"


# --- Creación automática de grupos y usuarios al migrar---
@receiver(post_migrate)
def crear_grupos_y_usuarios(sender, **kwargs):
    # Se ejecuta para la app de 'ventas' 
    if sender.label != 'ventas':
        return

    admin_group, _ = Group.objects.get_or_create(name='Administrador')
    vendedor_group, _ = Group.objects.get_or_create(name='Vendedor')

    from django.contrib.auth import get_user_model
    UsuarioModel = get_user_model()

    # Usuarios del Sistema
    for username, password in [('GermanB', 'Admin123+'), ('CarmenB', 'Admin123+')]:
        if not UsuarioModel.objects.filter(username=username).exists():
            user = UsuarioModel.objects.create_superuser(
                username=username,
                password=password,
                email=f'{username.lower()}@correo.com',
                rol='admin',
                is_staff=True,
                is_superuser=True
            )
            user.groups.add(admin_group)

    if not UsuarioModel.objects.filter(username='JuanP').exists():
        vendedor = UsuarioModel.objects.create_user(
            username='JuanP',
            password='Vendedor123+',
            email='juanP@correo.com',
            rol='vendedor',
            is_staff=False,
            is_superuser=False
        )
        vendedor.groups.add(vendedor_group)