from django.db import models

# Modelos para el inventario de la tienda.
class Producto(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del producto")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código del producto")
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad disponible")
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio del producto")

    def __str__(self):
        return f"{self.nombre} ({self.codigo}) - Stock: {self.cantidad}, Precio: ${self.precio}"

# Modelos para los clientes de la tienda.
class Cliente(models.Model):
    rut = models.CharField(max_length=12, verbose_name="RUT del cliente")
    # Este boleano define el flujo logico del requerimiento 
    es_habitual = models.BooleanField(default=False, verbose_name="¿Cliente habitual?")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del cliente")
    correo_electronico = models.EmailField(verbose_name="Correo electrónico del cliente")
    telefono = models.CharField(max_length=15, verbose_name="Teléfono del cliente")

    def __str__(self):
        return {self.rut}

class Venta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, verbose_name="Producto")    
    cantidad_vendida = models.PositiveIntegerField(verbose_name="Cantidad vendida")
    total_venta = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total de la venta")
    fecha_venta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de la venta")

    def __str__(self):
        return f"Venta de {self.id} - Cliente: {self.cliente.rut}"

    