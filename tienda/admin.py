from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html
from .models import Producto, Cliente, Venta, DetalleVenta

# ==============================================================================
# CONFIGURACIÓN GENERAL DEL PANEL
# ==============================================================================
admin.site.site_header = "Administración - Sistema de Ventas"
admin.site.site_title = "Admin Sistema de Ventas"
admin.site.index_title = "Panel de Control"


# ==============================================================================
# ADMIN: PRODUCTO
# ==============================================================================
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'formato_precio', 'mostrar_stock', 'activo')
    search_fields = ('nombre', 'codigo')
    list_filter = ('activo', 'stock')
    ordering = ('nombre', 'stock')
    list_editable = ('activo',)
    list_per_page = 20

    @admin.display(description="Precio", ordering='precio')
    def formato_precio(self, obj):
        return f"${obj.precio:,.2f}"

    @admin.display(description="Stock Disponible", ordering='stock')
    def mostrar_stock(self, obj):
        if obj.stock <= 0:
            return format_html('<span style="color: #ef4444; font-weight: bold;">Sin Stock (0)</span>')
        elif obj.stock <= 5:
            return format_html('<span style="color: #f59e0b; font-weight: bold;">Crítico ({})</span>', obj.stock)
        return format_html('<span style="color: #10b981; font-weight: bold;">{}</span>', obj.stock)


# ==============================================================================
# ADMIN: CLIENTE
# ==============================================================================
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'correo_electronico', 'telefono', 'es_habitual')
    search_fields = ('rut', 'nombre', 'correo_electronico', 'telefono')
    list_filter = ('es_habitual',)
    ordering = ('nombre',)
    list_per_page = 20


# ==============================================================================
# INLINE: DETALLE DE VENTA
# ==============================================================================
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    min_num = 1
    fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal_calculado')
    readonly_fields = ('subtotal_calculado',)

    @admin.display(description="Subtotal")
    def subtotal_calculado(self, obj):
        if obj.pk and obj.subtotal:
            return f"${obj.subtotal:,.2f}"
        return "$0.00"


# ==============================================================================
# ADMIN: VENTA
# ==============================================================================
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    inlines = [DetalleVentaInline]
    list_display = ('id', 'fecha_venta', 'cliente', 'items_vendidos', 'mostrar_total')
    list_filter = (
        'fecha_venta',
        ('fecha_venta', admin.DateFieldListFilter),
        'cliente__es_habitual',
    )
    search_fields = ('cliente__rut', 'cliente__nombre')
    date_hierarchy = 'fecha_venta'
    readonly_fields = ('fecha_venta', 'mostrar_total_formulario')
    ordering = ('-fecha_venta',)
    list_per_page = 20

    def get_search_results(self, request, queryset, search_term):
        """Búsqueda inteligente: por ID exacto si es número, o por RUT/nombre del cliente."""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            search_term = search_term.strip()
            if search_term.isdigit():
                queryset |= self.model.objects.filter(
                    Q(id=int(search_term)) |
                    Q(cliente__rut__icontains=search_term)
                )
            else:
                queryset |= self.model.objects.filter(
                    Q(cliente__rut__icontains=search_term) |
                    Q(cliente__nombre__icontains=search_term)
                )
        return queryset, use_distinct

    fieldsets = (
        ('Información General de la Venta', {
            'fields': ('cliente', 'fecha_venta', 'mostrar_total_formulario', 'observaciones')
        }),
    )

    @admin.display(description="Total Venta", ordering='total_venta')
    def mostrar_total(self, obj):
        total_formateado = f"${obj.total_venta:,.2f}"
        return format_html('<strong style="color: #fb923c;">{}</strong>', total_formateado)

    @admin.display(description="Total Calculado")
    def mostrar_total_formulario(self, obj):
        if obj.pk:
            total_formateado = f"${obj.total_venta:,.2f}"
            return format_html('<span style="font-size: 1.25rem; font-weight: 700; color: #fb923c;">{}</span>', total_formateado)
        return "Se calculará automáticamente al guardar los detalles."

    @admin.display(description="N° Productos")
    def items_vendidos(self, obj):
        return obj.detalles.count()

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Recalcular automáticamente el total de la venta sumando todos los detalles
        form.instance.calcular_total()