from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal

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
    Fecha_Venta=models.DateField(default=timezone.now) #campo modificable
    Cliente=models.ForeignKey(Cliente,on_delete=models.PROTECT, null=False, blank=False)
    Total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])

class Compra(models.Model):
    Id_Compra=models.AutoField(primary_key=True)
    Fecha_Compra=models.DateField(default=timezone.now)
    Proveedor=models.ForeignKey(Proveedor,on_delete=models.PROTECT, null=False, blank=False)
    SubTotal=models.DecimalField(max_digits=12,decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    Total=models.DecimalField(max_digits=12,decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])