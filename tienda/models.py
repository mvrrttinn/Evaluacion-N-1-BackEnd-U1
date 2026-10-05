from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

# ==============================================================================
# MODELO: CLIENTE
# ==============================================================================
class Cliente(models.Model):
    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT del cliente")
    es_habitual = models.BooleanField(default=False, verbose_name="¿Cliente habitual?")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del cliente")
    correo_electronico = models.EmailField(blank=True, null=True, verbose_name="Correo electrónico")
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre']

    def clean(self):
        super().clean()
        if self.rut:
            rut_limpio = str(self.rut).replace(".", "").replace("-", "").strip().upper()
            if len(rut_limpio) >= 2:
                self.rut = f"{rut_limpio[:-1]}-{rut_limpio[-1]}"

    def save(self, *args, **kwargs):
        if self.rut:
            rut_limpio = str(self.rut).replace(".", "").replace("-", "").strip().upper()
            if len(rut_limpio) >= 2:
                self.rut = f"{rut_limpio[:-1]}-{rut_limpio[-1]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.rut})"


# ==============================================================================
# MODELO: PRODUCTO
# ==============================================================================
class Producto(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del producto")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código del producto")
    stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0, message="El stock no puede ser negativo.")],
        verbose_name="Stock disponible"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'), message="El precio debe ser mayor o igual a 1.")],
        verbose_name="Precio del producto"
    )
    activo = models.BooleanField(default=True, verbose_name="¿Producto activo?")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre']

    def clean(self):
        super().clean()
        if self.precio is not None and self.precio < Decimal('1.00'):
            raise ValidationError({'precio': "El precio de un Producto jamás puede ser negativo ni cero (mínimo 1)."})
        if self.stock is not None and self.stock < 0:
            raise ValidationError({'stock': "El stock del Producto no puede ser negativo."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.codigo}) - Stock: {self.stock} - ${self.precio:,.2f}"


# ==============================================================================
# MODELO: VENTA
# ==============================================================================
class Venta(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="ventas",
        verbose_name="Cliente"
    )
    fecha_venta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de la venta")
    total_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total de la venta"
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_venta']

    def calcular_total(self):
        """Calcula el total sumando los subtotales de todos sus detalles."""
        total = sum((detalle.subtotal for detalle in self.detalles.all()), Decimal('0.00'))
        self.total_venta = total
        Venta.objects.filter(id=self.id).update(total_venta=total)
        return total

    def __str__(self):
        return f"Venta #{self.id} - {self.cliente.nombre} - ${self.total_venta:,.2f} ({self.fecha_venta.strftime('%d/%m/%Y %H:%M') if self.fecha_venta else 'Pendiente'})"


# ==============================================================================
# MODELO: DETALLE DE VENTA
# ==============================================================================
class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Venta"
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        verbose_name="Producto"
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1, message="La cantidad debe ser mayor a 0.")],
        verbose_name="Cantidad vendida"
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'), message="El precio unitario debe ser mayor a 0.")],
        verbose_name="Precio unitario"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Subtotal"
    )

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad < 1:
            raise ValidationError({'cantidad': "La cantidad vendida debe ser mayor a 0."})

        if self.producto_id:
            # Obtenemos la instancia fresca del producto desde la base de datos
            producto_db = Producto.objects.get(pk=self.producto.pk)
            
            # Si estamos editando un detalle existente, calculamos la diferencia de stock
            stock_disponible = producto_db.stock
            if self.pk:
                detalle_original = DetalleVenta.objects.get(pk=self.pk)
                # Si no cambió de producto, sumamos lo que ya tenía reservado
                if detalle_original.producto_id == self.producto_id:
                    stock_disponible += detalle_original.cantidad

            if self.cantidad is not None and self.cantidad > stock_disponible:
                raise ValidationError({
                    'cantidad': f"No hay stock suficiente para '{producto_db.nombre}'. Stock disponible: {stock_disponible}, solicitado: {self.cantidad}."
                })

    def save(self, *args, **kwargs):
        # Asignar precio unitario automáticamente del producto si no viene definido
        if not self.precio_unitario and self.producto_id:
            self.precio_unitario = self.producto.precio

        # Calcular subtotal
        self.subtotal = Decimal(self.cantidad) * Decimal(self.precio_unitario)
        
        self.full_clean()

        with transaction.atomic():
            # Manejo del stock
            if self.pk:
                detalle_original = DetalleVenta.objects.get(pk=self.pk)
                if detalle_original.producto_id == self.producto_id:
                    # Ajustar diferencia de stock en el mismo producto
                    diferencia = self.cantidad - detalle_original.cantidad
                    self.producto.stock -= diferencia
                    self.producto.save(update_fields=['stock'])
                else:
                    # Restaurar stock del producto anterior
                    producto_antiguo = detalle_original.producto
                    producto_antiguo.stock += detalle_original.cantidad
                    producto_antiguo.save(update_fields=['stock'])
                    # Descontar stock del nuevo producto
                    self.producto.stock -= self.cantidad
                    self.producto.save(update_fields=['stock'])
            else:
                # Registro nuevo: descontar stock
                self.producto.stock -= self.cantidad
                self.producto.save(update_fields=['stock'])

            super().save(*args, **kwargs)
            
            # Recalcular total de la venta padre
            if self.venta_id:
                self.venta.calcular_total()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            # Devolver stock al producto
            self.producto.stock += self.cantidad
            self.producto.save(update_fields=['stock'])
            
            venta = self.venta
            super().delete(*args, **kwargs)
            
            # Recalcular total de la venta
            if venta:
                venta.calcular_total()

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (${self.precio_unitario:,.2f}) = ${self.subtotal:,.2f}"