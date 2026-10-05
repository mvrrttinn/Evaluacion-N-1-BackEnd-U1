from django.contrib import admin
from .models import Producto, Cliente, Venta

admin.site.site_header = "Administración - Sistema de Ventas"
admin.site.site_title = "Admin Sistema de Ventas"
admin.site.index_title = "Panel de Control"

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'precio', 'stock', 'activo')
    search_fields = ('nombre', 'codigo')
    list_filter = ('activo',)
    ordering = ('nombre', 'stock')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'correo_electronico', 'telefono', 'es_habitual')
    search_fields = ('rut', 'nombre', 'correo_electronico')
    list_filter = ('es_habitual',)

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'producto', 'cantidad_vendida', 'total_venta', 'fecha_venta')
    list_filter = ('fecha_venta',)
    search_fields = ('cliente__nombre', 'cliente__rut', 'producto__nombre')