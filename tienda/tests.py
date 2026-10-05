from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Producto, Cliente, Venta, DetalleVenta
from .forms import ProductoForm, DetalleVentaForm


class SistemaVentasBusinessRulesTestCase(TestCase):
    def setUp(self):
        # Crear cliente de prueba
        self.cliente = Cliente.objects.create(
            rut="11.111.111-1",
            nombre="Juan Pérez",
            es_habitual=True,
            telefono="+56911112222"
        )
        # Crear producto con stock 10 y precio 500.00
        self.producto = Producto.objects.create(
            nombre="Teclado Mecánico",
            codigo="TEC-001",
            stock=10,
            precio=Decimal("500.00"),
            activo=True
        )

    # --------------------------------------------------------------------------
    # 1. VALIDACIONES DE PRODUCTO
    # --------------------------------------------------------------------------
    def test_precio_producto_no_puede_ser_cero_ni_negativo(self):
        """El precio de un Producto jamás puede ser negativo ni cero."""
        prod_invalido = Producto(
            nombre="Mouse",
            codigo="MOU-001",
            stock=5,
            precio=Decimal("0.00")
        )
        with self.assertRaises(ValidationError):
            prod_invalido.save()

        prod_negativo = Producto(
            nombre="Mouse 2",
            codigo="MOU-002",
            stock=5,
            precio=Decimal("-10.00")
        )
        with self.assertRaises(ValidationError):
            prod_negativo.save()

    def test_stock_producto_no_puede_ser_negativo(self):
        """El stock de un Producto no puede ser negativo."""
        prod_stock_neg = Producto(
            nombre="Monitor",
            codigo="MON-001",
            stock=-1,
            precio=Decimal("1500.00")
        )
        with self.assertRaises(ValidationError):
            prod_stock_neg.save()

    # --------------------------------------------------------------------------
    # 2. VALIDACIONES Y LÓGICA DE DETALLE DE VENTA Y DESCUENTO DE STOCK
    # --------------------------------------------------------------------------
    def test_venta_descuenta_stock_y_calcula_total(self):
        """Al guardar un DetalleVenta, el stock del Producto se descuenta y el total de la Venta se calcula."""
        venta = Venta.objects.create(cliente=self.cliente)

        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=3,
            precio_unitario=self.producto.precio
        )

        # Verificar subtotal
        self.assertEqual(detalle.subtotal, Decimal("1500.00"))

        # Verificar que el stock se descontó (10 - 3 = 7)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)

        # Verificar que el total de la venta es 1500.00
        venta.refresh_from_db()
        self.assertEqual(venta.total_venta, Decimal("1500.00"))

    def test_no_permite_vender_mas_que_el_stock_disponible(self):
        """La cantidad vendida no puede superar el stock disponible del producto."""
        venta = Venta.objects.create(cliente=self.cliente)

        detalle = DetalleVenta(
            venta=venta,
            producto=self.producto,
            cantidad=15,  # Stock es 10
            precio_unitario=self.producto.precio
        )
        with self.assertRaises(ValidationError):
            detalle.save()

    def test_anular_venta_restaura_stock(self):
        """Al eliminar/anular un DetalleVenta o Venta, el stock del Producto se restaura."""
        venta = Venta.objects.create(cliente=self.cliente)
        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=4,
            precio_unitario=self.producto.precio
        )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 6)

        # Eliminar detalle
        detalle.delete()

        # Stock debe regresar a 10
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    # --------------------------------------------------------------------------
    # 3. VALIDACIONES EN FORMULARIOS
    # --------------------------------------------------------------------------
    def test_formulario_producto_valida_precio_y_stock(self):
        """El formulario ProductoForm rechaza precios <= 0 y stock < 0."""
        form = ProductoForm(data={
            'nombre': 'Audífonos',
            'codigo': 'AUD-001',
            'stock': -5,
            'precio': 0,
            'activo': True
        })
        self.assertFalse(form.is_valid())
        self.assertIn('precio', form.errors)
        self.assertIn('stock', form.errors)

    def test_formulario_detalle_venta_valida_stock_insuficiente(self):
        """El formulario DetalleVentaForm valida que no se supere el stock disponible."""
        form = DetalleVentaForm(data={
            'producto': self.producto.id,
            'cantidad': 25
        })
        self.assertFalse(form.is_valid())
        self.assertIn('cantidad', form.errors)
