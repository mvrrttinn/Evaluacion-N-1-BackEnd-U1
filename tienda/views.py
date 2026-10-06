from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction, models
from django.db.models import Q
from datetime import datetime
from decimal import Decimal

from .models import Producto, Cliente, Venta, DetalleVenta
from .forms import ProductoForm, ClienteForm, VentaForm, DetalleVentaForm


# ==============================================================================
# CRUD: PRODUCTOS
# ==============================================================================

def inventario(request):
    """Listado paginado de productos con búsqueda por nombre o código."""
    query = request.GET.get('q', '').strip()
    filtro_estado = request.GET.get('estado', '')

    productos_list = Producto.objects.all().order_by('nombre')

    if query:
        productos_list = productos_list.filter(
            Q(nombre__icontains=query) | Q(codigo__icontains=query)
        )

    if filtro_estado == 'activo':
        productos_list = productos_list.filter(activo=True)
    elif filtro_estado == 'inactivo':
        productos_list = productos_list.filter(activo=False)
    elif filtro_estado == 'bajo_stock':
        productos_list = productos_list.filter(stock__lte=5)

    # Paginación: 8 productos por página
    paginator = Paginator(productos_list, 8)
    page = request.GET.get('page')

    try:
        productos = paginator.page(page)
    except PageNotAnInteger:
        productos = paginator.page(1)
    except EmptyPage:
        productos = paginator.page(paginator.num_pages)

    return render(request, 'tienda/inventario.html', {
        'productos': productos,
        'query': query,
        'filtro_estado': filtro_estado,
    })


def agregar_producto(request):
    """Creación de nuevo producto con validación estricta de precio y stock."""
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f"¡Producto '{producto.nombre}' registrado exitosamente con código {producto.codigo}!")
            return redirect('inventario')
        else:
            messages.error(request, "Error al registrar el producto. Por favor revise las validaciones del formulario.")
    else:
        form = ProductoForm()

    return render(request, 'tienda/nuevo_producto.html', {'form': form})


def editar_producto(request, id):
    """Edición de producto existente."""
    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f"¡Producto '{producto.nombre}' actualizado correctamente!")
            return redirect('inventario')
        else:
            messages.error(request, "Error al actualizar el producto. Verifique los datos ingresados.")
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'tienda/editar_producto.html', {
        'form': form,
        'producto': producto
    })


def eliminar_producto(request, id):
    """Eliminación de producto protegiendo integridad referencial de ventas."""
    producto = get_object_or_404(Producto, id=id)

    if producto.detalles_venta.exists():
        messages.error(
            request,
            f"No se puede eliminar '{producto.nombre}' porque registra ventas asociadas en el historial. Puede desactivarlo en su lugar."
        )
    else:
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f"El producto '{nombre}' fue eliminado exitosamente del inventario.")

    return redirect('inventario')


# ==============================================================================
# CRUD: VENTAS
# ==============================================================================

def historial_ventas(request):
    """Listado paginado de ventas con filtros por rango de fecha y búsqueda por RUT/Cliente."""
    query = request.GET.get('q', '').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin = request.GET.get('fecha_fin', '').strip()

    ventas_list = Venta.objects.select_related('cliente').prefetch_related('detalles__producto').all().order_by('-fecha_venta')

    if query:
        if query.isdigit():
            ventas_list = ventas_list.filter(
                Q(id=int(query)) |
                Q(cliente__rut__icontains=query)
            )
        else:
            ventas_list = ventas_list.filter(
                Q(cliente__rut__icontains=query) |
                Q(cliente__nombre__icontains=query)
            )

    if fecha_inicio:
        try:
            inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            ventas_list = ventas_list.filter(fecha_venta__date__gte=inicio_dt.date())
        except ValueError:
            pass

    if fecha_fin:
        try:
            fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            ventas_list = ventas_list.filter(fecha_venta__date__lte=fin_dt.date())
        except ValueError:
            pass

    # Paginación: 8 ventas por página
    paginator = Paginator(ventas_list, 8)
    page = request.GET.get('page')

    try:
        ventas = paginator.page(page)
    except PageNotAnInteger:
        ventas = paginator.page(1)
    except EmptyPage:
        ventas = paginator.page(paginator.num_pages)

    return render(request, 'tienda/historial_ventas.html', {
        'ventas': ventas,
        'query': query,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })


def detalle_venta(request, id):
    """Detalle completo tipo comprobante de una venta específica."""
    venta = get_object_or_404(Venta.objects.select_related('cliente').prefetch_related('detalles__producto'), id=id)
    return render(request, 'tienda/detalle_venta.html', {'venta': venta})


def registrar_venta(request):
    """
    Registro transaccional de venta con verificación y descuento de stock,
    cálculo automático de total y validación completa de clientes.
    """
    if request.method == 'POST':
        cliente_form = ClienteForm(request.POST)
        venta_form = VentaForm(request.POST)
        detalle_form = DetalleVentaForm(request.POST)

        if cliente_form.is_valid() and venta_form.is_valid() and detalle_form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardar o recuperar cliente
                    cliente = cliente_form.save(commit=True)

                    # 2. Crear cabecera de la venta
                    venta = venta_form.save(commit=False)
                    venta.cliente = cliente
                    venta.total_venta = Decimal('0.00')
                    venta.save()

                    # 3. Crear detalle de la venta (esto descuenta el stock automáticamente en su save())
                    detalle = detalle_form.save(commit=False)
                    detalle.venta = venta
                    detalle.precio_unitario = detalle.producto.precio
                    detalle.save()

                    # 4. Confirmación al usuario
                    messages.success(
                        request,
                        f"¡Venta #{venta.id} por ${venta.total_venta:,.2f} procesada exitosamente! Stock de '{detalle.producto.nombre}' actualizado a {detalle.producto.stock} unidades."
                    )
                    return redirect('detalle_venta', id=venta.id)

            except Exception as e:
                messages.error(request, f"Error al procesar la venta: {str(e)}")
        else:
            messages.error(request, "Por favor corrija los errores indicados en el formulario.")
    else:
        cliente_form = ClienteForm()
        venta_form = VentaForm()
        detalle_form = DetalleVentaForm()

    return render(request, 'tienda/registrar_venta.html', {
        'cliente_form': cliente_form,
        'venta_form': venta_form,
        'detalle_form': detalle_form,
    })


def eliminar_venta(request, id):
    """Anulación/eliminación de una venta restaurando el stock de los productos vendidos."""
    venta = get_object_or_404(Venta, id=id)

    with transaction.atomic():
        # Al eliminar los detalles individualmente o vía cascade con nuestro delete custom,
        # el stock se restaura automáticamente.
        for detalle in venta.detalles.all():
            detalle.delete()
        venta_id = venta.id
        venta.delete()

    messages.success(request, f"La venta #{venta_id} ha sido anulada exitosamente y el stock de los productos fue restaurado.")
    return redirect('historial_ventas')