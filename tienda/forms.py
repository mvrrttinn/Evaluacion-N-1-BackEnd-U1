from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Producto, Cliente, Venta, DetalleVenta

# ==============================================================================
# VALIDACIÓN DE RUT CHILENO (MÓDULO 11)
# ==============================================================================
def validar_rut_chile(rut_completo):
    """Valida formato y dígito verificador del RUT chileno."""
    if not rut_completo:
        return False
    try:
        rut_limpio = str(rut_completo).replace(".", "").replace("-", "").strip().upper()
        if len(rut_limpio) < 2:
            return False
        cuerpo = rut_limpio[:-1]
        dv = rut_limpio[-1]
        
        if not cuerpo.isdigit():
            return False

        suma = 0
        multiplo = 2
        for r in reversed(cuerpo):
            suma += int(r) * multiplo
            multiplo += 1
            if multiplo == 8:
                multiplo = 2
                
        esperado = 11 - (suma % 11)
        if esperado == 11:
            dv_esperado = "0"
        elif esperado == 10:
            dv_esperado = "K"
        else:
            dv_esperado = str(esperado)
            
        return dv_esperado == dv
    except Exception:
        return False


# ==============================================================================
# FORMULARIO: PRODUCTO
# ==============================================================================
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'codigo', 'stock', 'precio', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Arroz Grado 1'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. PROD-001'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '0.01'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').strip().upper()
        # Verificar unicidad respetando si se está editando la misma instancia
        qs = Producto.objects.filter(codigo=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un producto registrado con este código.")
        return codigo

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is None or precio < Decimal('1.00'):
            raise ValidationError("El precio del Producto jamás puede ser negativo ni cero (mínimo $1).")
        return precio

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None or stock < 0:
            raise ValidationError("El stock del Producto no puede ser negativo.")
        return stock


# ==============================================================================
# FORMULARIO: CLIENTE
# ==============================================================================
class ClienteForm(forms.ModelForm):
    rut = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12.345.678-9'})
    )
    nombre = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'})
    )
    telefono = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56912345678'})
    )
    correo_electronico = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'cliente@ejemplo.com'})
    )

    class Meta:
        model = Cliente
        fields = ['rut', 'es_habitual', 'nombre', 'correo_electronico', 'telefono']

    def clean_rut(self):
        rut = self.cleaned_data.get('rut', '').strip()
        if not validar_rut_chile(rut):
            raise ValidationError("El RUT ingresado no es válido (verifique el formato y dígito verificador).")
        # Formatear el RUT a formato estándar sin puntos y con guión
        rut_limpio = rut.replace(".", "").replace("-", "").upper()
        return f"{rut_limpio[:-1]}-{rut_limpio[-1]}"

    def validate_unique(self):
        # Permitir que clientes recurrentes compren múltiples veces con el mismo RUT sin error de unicidad
        pass

    def clean(self):
        cleaned_data = super().clean()
        es_habitual = cleaned_data.get('es_habitual')
        nombre = cleaned_data.get('nombre')

        if es_habitual and not nombre:
            self.add_error('nombre', "Para marcar como cliente habitual, el nombre es obligatorio.")

        return cleaned_data

    def save(self, commit=True):
        rut = self.cleaned_data.get('rut')
        cliente, created = Cliente.objects.get_or_create(
            rut=rut,
            defaults={
                'es_habitual': self.cleaned_data.get('es_habitual', False),
                'nombre': self.cleaned_data.get('nombre') or f"Cliente {rut}",
                'correo_electronico': self.cleaned_data.get('correo_electronico'),
                'telefono': self.cleaned_data.get('telefono'),
            }
        )

        if not created:
            cliente.es_habitual = self.cleaned_data.get('es_habitual', cliente.es_habitual)
            if self.cleaned_data.get('nombre'):
                cliente.nombre = self.cleaned_data.get('nombre')
            if self.cleaned_data.get('correo_electronico'):
                cliente.correo_electronico = self.cleaned_data.get('correo_electronico')
            if self.cleaned_data.get('telefono'):
                cliente.telefono = self.cleaned_data.get('telefono')
            if commit:
                cliente.save()

        return cliente


# ==============================================================================
# FORMULARIO: REGISTRO DE VENTA Y DETALLES
# ==============================================================================
class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observaciones opcionales...'}),
        }


class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['producto', 'cantidad']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar productos activos en el selector de ventas
        self.fields['producto'].queryset = Producto.objects.filter(activo=True)

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is None or cantidad < 1:
            raise ValidationError("La cantidad vendida debe ser mayor a 0.")
        return cantidad

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto')
        cantidad = cleaned_data.get('cantidad')

        if producto and cantidad:
            if cantidad > producto.stock:
                self.add_error(
                    'cantidad',
                    f"No hay stock suficiente para '{producto.nombre}'. Stock disponible: {producto.stock}, solicitado: {cantidad}."
                )
        return cleaned_data