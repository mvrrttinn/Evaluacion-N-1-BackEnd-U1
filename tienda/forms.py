from django import forms
from .models import Producto, Cliente, Venta

# Función auxiliar para validar el RUT chileno mediante algoritmo oficial (Módulo 11)
def validar_rut_chile(rut_completo):
    try:
        rut_limpio = rut_completo.replace(".", "").replace("-", "").upper()
        cuerpo = rut_limpio[:-1]
        dv = rut_limpio[-1]
        
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

# Formulario para registrar y actualizar productos
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'codigo', 'cantidad', 'precio']

# Formulario transaccional y de registro de clientes
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['rut', 'es_habitual', 'nombre', 'telefono']

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not validar_rut_chile(rut):
            raise forms.ValidationError("El RUT ingresado no es válido (verifique dígito verificador).")
        return rut

    def clean(self):
        cleaned_data = super().clean()
        es_habitual = cleaned_data.get('es_habitual')
        nombre = cleaned_data.get('nombre')

        if es_habitual and not nombre:
            self.add_error('nombre', "Para ser cliente habitual, el nombre es obligatorio.")
            
        return cleaned_data

    # Sobrescribimos el método save para manejar clientes recurrentes sin duplicar registros
    def save(self, commit=True):
        rut = self.cleaned_data.get('rut')
        # Buscamos si el cliente ya existe en la base de datos por su RUT
        cliente, created = Cliente.objects.get_or_create(rut=rut, defaults={
            'es_habitual': self.cleaned_data.get('es_habitual'),
            'nombre': self.cleaned_data.get('nombre'),
            'telefono': self.cleaned_data.get('telefono')
        })
        
        # Si ya existía pero ahora quiere ser habitual o actualizó sus datos, los actualizamos
        if not created:
            cliente.es_habitual = self.cleaned_data.get('es_habitual')
            if self.cleaned_data.get('nombre'):
                cliente.nombre = self.cleaned_data.get('nombre')
            if self.cleaned_data.get('telefono'):
                cliente.telefono = self.cleaned_data.get('telefono')
            if commit:
                cliente.save()
                
        return cliente

# Formulario para procesar la venta
class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['producto', 'cantidad_vendida']