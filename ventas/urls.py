from django.urls import path

from . import views

urlpatterns = [
    path("", views.user_login, name="login"),
    path('login/', views.user_login, name='login'),
    path("logout/", views.user_logout, name="logout"),
    path("register/", views.user_register, name="register"),
    path("dashboard/", views.index, name="dashboard"),
    path("productos/", views.productos_lista, name="productos_lista"),
    path("proveedores/", views.proveedores_lista, name="proveedores_lista"),
    path("clientes/", views.clientes_lista, name="clientes_lista"),
    path('clientes/registrar/', views.clientes_registrar, name='clientes_registrar'),
    path("ventas/", views.ventas_lista, name="ventas_lista"),
]