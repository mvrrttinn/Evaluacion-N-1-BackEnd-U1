from django.urls import path
from . import views

urlpatterns = [
    # CRUD Productos
    path('', views.inventario, name='inventario'),
    path('producto/nuevo/', views.agregar_producto, name='agregar_producto'),
    path('producto/editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('producto/eliminar/<int:id>/', views.eliminar_producto, name='eliminar_producto'),

    # CRUD Ventas
    path('venta/nueva/', views.registrar_venta, name='registrar_venta'),
    path('venta/historial/', views.historial_ventas, name='historial_ventas'),
    path('venta/detalle/<int:id>/', views.detalle_venta, name='detalle_venta'),
    path('venta/eliminar/<int:id>/', views.eliminar_venta, name='eliminar_venta'),
]