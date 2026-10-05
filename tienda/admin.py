from django.contrib import admin
from .models import Producto

# Register your models here.

class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock', 'activo')
    search_fields = ('nombre','codigo',)
    list_filter = ('activo',)
    ordering = ('nombre','stock',)

admin.site.register(model_or_iterable=Producto, admin_class=ProductoAdmin)