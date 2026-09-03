from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Cliente, Venta
from .forms import ProductoForm, ClienteForm, VentaForm 

# 1. Mostrar listado de productos disponibles en el inventario
def inventario(request):
    # Consulta a la base de datos para obtener todos los productos
    productos = Producto.objects.all()
    return render(request, 'tienda/inventario.html', {'productos': productos})

# 2. Regisrar el producto a vender
def agregar_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid(): # Valida los datos de entrada
            form.save()
            return redirect('inventario')  # Redirige al listado de productos después de guardar
    else:
        form = ProductoForm()
    return render(request, 'tienda/nuevo_producto.html', {'form': form})

# 3. Eliminar productos
def eliminar_producto(request, id):
    # Busca el producto por su ID, si no lo encuentra devuelve un error 404
    producto = get_object_or_404(Producto, id=id)
    producto.delete() 
    return redirect('inventario')  # Redirige al listado de productos después de eliminar

# 4. Registrar ventas y actualizar stock
def registrar_venta(request):
    if request.method == 'POST':
        cliente_form = ClienteForm(request.POST)
        venta_form = VentaForm(request.POST)
        
        if cliente_form.is_valid() and venta_form.is_valid():
            venta = venta_form.save(commit=False)
            producto = venta.producto
            cantidad_solicitada = venta.cantidad_vendida
            
            if cantidad_solicitada <= producto.cantidad:
                # Actualizar stock
                producto.cantidad -= cantidad_solicitada
                producto.save()
                
                # Obtener datos limpios del cliente desde el formulario
                rut = cliente_form.cleaned_data.get('rut')
                es_habitual = cliente_form.cleaned_data.get('es_habitual')
                nombre = cliente_form.cleaned_data.get('nombre')
                telefono = cliente_form.cleaned_data.get('telefono')
                
                # Buscar si el cliente ya existe o crearlo si es nuevo
                cliente, created = Cliente.objects.get_or_create(rut=rut, defaults={
                    'es_habitual': es_habitual,
                    'nombre': nombre,
                    'telefono': telefono
                })
                
                # Si ya existía, actualizamos sus datos por si cambió a habitual
                if not created:
                    cliente.es_habitual = es_habitual
                    if nombre:
                        cliente.nombre = nombre
                    if telefono:
                        cliente.telefono = telefono
                    cliente.save()
                
                # Guardar la venta vinculada al cliente y calcular total
                venta.cliente = cliente
                venta.total_venta = cantidad_solicitada * producto.precio
                venta.save()
                
                return redirect('historial_ventas')
            else:
                venta_form.add_error('cantidad_vendida', 'No hay stock suficiente.')
    else:
        cliente_form = ClienteForm()
        venta_form = VentaForm()
        
    return render(request, 'tienda/registrar_venta.html', {
        'cliente_form': cliente_form,
        'venta_form': venta_form
    })
# 5. Listar ventas realizadas
def historial_ventas(request):
    ventas = Venta.objects.all().order_by('-fecha_venta') # Ordenadas de la más reciente a la más antigua
    return render(request, 'tienda/historial_ventas.html', {'ventas': ventas})