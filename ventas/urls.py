from django.urls import path

from . import views

urlpatterns = [
    path("", views.user_login, name="login"),
    path('login/', views.user_login, name='login'),
    path("logout/", views.user_logout, name="logout"),
    path("register/", views.user_register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("productos/", views.productos_lista, name="productos_lista"),
    path("productos/registrar/", views.productos_registrar, name="productos_registrar"),
    path("productos/marcas/", views.marca_lista, name="marca_lista"),
    path("productos/categorias/", views.categoria_lista, name="categoria_lista"),
    path("clientes/", views.clientes_lista, name="clientes_lista"),
    path('clientes/registrar/', views.clientes_registrar, name='clientes_registrar'),
    path("ventas/", views.ventas_lista, name="ventas_lista"),
    path("ventas_registrar/", views.ventas_registrar, name="ventas_registrar"),
    path('ventas/detalle/<int:pk>/', views.ventas_detalle, name='ventas_detalle')
]