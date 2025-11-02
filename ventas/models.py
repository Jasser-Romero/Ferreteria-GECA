from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum, Q, CheckConstraint, UniqueConstraint
from django.core.exceptions import ValidationError

# Librerias para Manejo de Usuarios
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

# Create your models here.
class Cliente(models.Model):
    Id_Cliente=models.AutoField(primary_key=True)
    PrimerNombre=models.CharField(max_length=50)
    SegundoNombre=models.CharField(max_length=50)
    PrimerApellido=models.CharField(max_length=50)
    SegundoApellido=models.CharField(max_length=50)
    Activo=models.BooleanField(default=True)

class Marca(models.Model):
    Id_Marca=models.AutoField(primary_key=True)
    NombreMarca=models.CharField(max_length=50)
    Activo=models.BooleanField(default=True)

class Categoria(models.Model):
    Id_Categoria=models.AutoField(primary_key=True)
    NombreCategoria=models.CharField(max_length=50)
    Activo=models.BooleanField(default=True)

class Proveedor(models.Model):
    Id_Proveedor=models.AutoField(primary_key=True)
    NombreEmpresa=models.CharField(max_length=50)
    Telefono=models.CharField(max_length=8,
        validators=[
        RegexValidator(regex=r'^\d{8}$', message='Debe tener 8 digitos')
        ])

class Producto(models.Model):
    Id_Producto=models.AutoField(primary_key=True)
    NombreProducto=models.CharField(max_length=50)
    Descripcion=models.CharField(max_length=200)
    Existencia=models.IntegerField(
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
    Proveedor=models.ForeignKey(Proveedor, on_delete=models.PROTECT, null=False, blank=False)

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
    
    def save(self, *args, **kwargs):
        if self.PrecioUnitario is None:
            self.PrecioUnitario = self.Producto.Precio
        self.SubTotal = (Decimal(self.CantidadVendida)* self.PrecioUnitario).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
        #todo:actualiza total de la venta
        self.Venta.recalcular_total(save=True)

class Compra(models.Model):
    Id_Compra=models.AutoField(primary_key=True)
    Fecha_Compra=models.DateField(default=timezone.now)
    Proveedor=models.ForeignKey(Proveedor,on_delete=models.PROTECT, null=False, blank=False)
    SubTotal=models.DecimalField(max_digits=12,decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    Total=models.DecimalField(max_digits=12,decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])

    class Meta:
        constraints = [
            CheckConstraint(check=Q(SubTotal__gte=0), name='compra_subtotal_ge_0'),
            CheckConstraint(check=Q(Total__gte=0), name='compra_total_ge_0'),
        ]
        ordering = ['-Fecha_Compra', '-Id_Compra']

    def __str__(self):
        return f"Compra #{self.Id_Compra} ({self.Fecha_Compra})"

    def recalcular_totales(self, save=True):
        suma = self.detalles_compra.aggregate(s=Sum('SubTotalDC'))['s'] or Decimal('0.00')
        self.SubTotal = suma
        self.Total = self.SubTotal
        if save:
            self.save(update_fields=['SubTotal', 'Total'])

class CompraDetalle(models.Model):
    Compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles_compra')
    Producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_compra')

    CantidadC = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(999999)])
    PrecioC   = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    SubTotalDC= models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [
            UniqueConstraint(fields=['Compra', 'Producto'], name='compra_producto_unico'),
            CheckConstraint(check=Q(CantidadC__gte=1), name='compra_det_cantidad_ge_1'),
            CheckConstraint(check=Q(PrecioC__gte=0), name='compra_det_precio_ge_0'),
            CheckConstraint(check=Q(SubTotalDC__gte=0), name='compra_det_subtotal_ge_0'),
        ]

    def __str__(self):
        return f"{self.Producto.NombreProducto} x {self.CantidadC}"
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        # todo: Calcula el subtotal (moneda exacta)
        self.SubTotalDC = (Decimal(self.CantidadC) * self.PrecioC).quantize(Decimal('0.01'))

        # todo: Detectar si es creación o edición para calcular deltas de inventario
        old = None
        if self.pk:
            try:
                old = type(self).objects.select_related('Producto').get(pk=self.pk)
            except type(self).DoesNotExist:
                old = None

        super().save(*args, **kwargs)  # guarda el detalle primero

        # Ajustar inventario según delta
        if old is None:
            # creación: sumar todo a stock del producto actual
            prod = self.Producto
            prod.Existencia = (prod.Existencia or 0) + self.CantidadC
            prod.save(update_fields=['Existencia'])
        else:
            if old.Producto_id != self.Producto_id:
                # cambió el producto: revertir en el viejo y sumar en el nuevo
                prod_old = old.Producto
                if (prod_old.Existencia or 0) - old.CantidadC < 0:
                    raise ValidationError("No hay stock suficiente para revertir en el producto anterior.")
                prod_old.Existencia = prod_old.Existencia - old.CantidadC
                prod_old.save(update_fields=['Existencia'])

                prod_new = self.Producto
                prod_new.Existencia = (prod_new.Existencia or 0) + self.CantidadC
                prod_new.save(update_fields=['Existencia'])
            else:
                # mismo producto: aplicar delta de cantidad
                delta = self.CantidadC - old.CantidadC
                if delta != 0:
                    prod = self.Producto
                    # Como es compra, delta positivo suma; si delta negativo, resta
                    if delta < 0 and (prod.Existencia or 0) + delta < 0:
                        raise ValidationError("No hay stock suficiente para disminuir por la edición de la compra.")
                    prod.Existencia = (prod.Existencia or 0) + delta
                    prod.save(update_fields=['Existencia'])

        # Recalcular totales de la compra
        self.Compra.recalcular_totales(save=True)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        # Revertir stock al eliminar el detalle de compra
        prod = self.Producto
        if (prod.Existencia or 0) - self.CantidadC < 0:
            # todo: Esto sirve para validar y avisar cuando se tenga valores negativos
            raise ValidationError("No hay stock suficiente para revertir esta compra (inventario quedaría negativo).")
        prod.Existencia = prod.Existencia - self.CantidadC
        prod.save(update_fields=['Existencia'])

        compra = self.Compra
        super().delete(*args, **kwargs)

        # Recalcular totales de la compra
        compra.recalcular_totales(save=True)

#todo: esta logica se hara después de la migracion del modelo de la bd
#Manejo de Usuarios en el Sistema
# class Usuario(AbstractUser):
#     ROL_CHOICES = [
#         ('admin', 'Administrador'),
#         ('vendedor', 'Vendedor'),
#     ]
#     rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='vendedor')

#     def __str__(self):
#         return f"{self.username} ({self.get_rol_display()})"
    
# # --- Creación automática de grupos y usuarios al migrar ---
# @receiver(post_migrate)
# def crear_grupos_y_usuarios(sender, **kwargs):
#     """
#     Crea los grupos (Administrador y Vendedor) y los usuarios iniciales si no existen.
#     Se ejecuta automáticamente después de cada migrate.
#     """
#     if sender.label != 'ventas':  
#         # Crear grupos
#         admin_group, _ = Group.objects.get_or_create(name='Administrador')
#         vendedor_group, _ = Group.objects.get_or_create(name='Vendedor')

#         # Crear usuarios administrador
#         for username, password in [('GermanB', 'Admin123+'), ('CarmenB', 'Admin123+')]:
#             if not Usuario.objects.filter(username=username).exists():
#                 user = Usuario.objects.create_superuser(
#                     username=username,
#                     password=password,
#                     email=f'{username.lower()}@correo.com',
#                     rol='admin',
#                     is_staff=True,
#                     is_superuser=True
#                 )
#                 user.groups.add(admin_group)
#                 print(f"✅ Usuario administrador creado: {username}")

#         # Crear usuario vendedor
#         if not Usuario.objects.filter(username='JaysonH').exists():
#             vendedor = Usuario.objects.create_user(
#                 username='JaysonH',
#                 password='Vendedor123+',
#                 email='jaysonH@correo.com',
#                 rol='vendedor',
#                 is_staff=False,
#                 is_superuser=False
#             )
#             vendedor.groups.add(vendedor_group)
#             print("✅ Usuario vendedor creado: JaysonH")

# todo: agregar los permisos de tablas a los grupos de usuarios (admin, vendedor)