from django.urls import path
from . import views

urlpatterns = [
    # Ruta principal que carga el inventario
    path('', views.inventario, name='inventario'),
    # Ruta para gestión de productos
    path('producto/nuevo/', views.agregar_producto, name='agregar_producto'),
    path('producto/eliminar/<int:id>/', views.eliminar_producto, name='eliminar_producto'),
    # Ruta para registrar ventas
    path('venta/nueva/', views.registrar_venta, name='registrar_venta'),
    path('venta/historial/', views.historial_ventas, name='historial_ventas') 
]