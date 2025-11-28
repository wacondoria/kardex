"""
Sistema de Licenciamiento para Kardex Valorizado
Genera claves maestras anuales con validación de fecha de vencimiento
"""

import hashlib
import base64
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import json

class LicenseManager:
    """
    Gestor de licencias con encriptación
    Usa una clave secreta que solo tú conoces
    """
    
    # CLAVE SECRETA - CÁMBIALA POR UNA ÚNICA TUYA
    # Para generar una nueva: Fernet.generate_key()
    SECRET_KEY = b'2kxvJxBjSpZbh06EhRiYkfgmrrV6DNY85-fRyHuuvMY='
    
    def __init__(self):
        self.cipher = Fernet(self.SECRET_KEY)
    
    def generar_licencia(self, fecha_vencimiento, empresa="", notas=""):
        """
        Genera una licencia maestra
        
        Args:
            fecha_vencimiento (datetime): Fecha de vencimiento
            empresa (str): Nombre de empresa (opcional, para tu control)
            notas (str): Notas adicionales (opcional)
            
        Returns:
            str: Código de licencia encriptado
        """
        datos_licencia = {
            'vencimiento': fecha_vencimiento.strftime('%Y-%m-%d'),
            'empresa': empresa,
            'notas': notas,
            'generada': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Convertir a JSON y encriptar
        datos_json = json.dumps(datos_licencia)
        licencia_encriptada = self.cipher.encrypt(datos_json.encode())
        
        # Convertir a string base64 legible
        licencia_str = base64.urlsafe_b64encode(licencia_encriptada).decode()
        
        # Formatear en bloques para mejor legibilidad
        licencia_formateada = '-'.join([licencia_str[i:i+4] for i in range(0, len(licencia_str), 4)])
        
        return licencia_formateada
    
    def validar_licencia(self, codigo_licencia):
        """
        Valida una licencia y retorna su información
        
        Args:
            codigo_licencia (str): Código de licencia a validar
            
        Returns:
            dict: Información de la licencia con estado de validez
        """
        try:
            # Limpiar formato y decodificar
            codigo_limpio = codigo_licencia.replace('-', '').replace(' ', '')
            licencia_encriptada = base64.urlsafe_b64decode(codigo_limpio.encode())
            
            # Desencriptar
            datos_json = self.cipher.decrypt(licencia_encriptada).decode()
            datos = json.loads(datos_json)
            
            # Parsear fecha de vencimiento
            fecha_venc = datetime.strptime(datos['vencimiento'], '%Y-%m-%d')
            fecha_actual = datetime.now()
            
            # Calcular días restantes
            dias_restantes = (fecha_venc - fecha_actual).days
            
            # Determinar estado
            if dias_restantes < 0:
                estado = 'VENCIDA'
                mensaje = f'Licencia vencida hace {abs(dias_restantes)} días'
            elif dias_restantes <= 30:
                estado = 'POR_VENCER'
                mensaje = f'⚠️ Licencia vence en {dias_restantes} días'
            else:
                estado = 'VIGENTE'
                mensaje = f'✓ Licencia vigente ({dias_restantes} días restantes)'
            
            return {
                'valida': True,
                'estado': estado,
                'mensaje': mensaje,
                'dias_restantes': dias_restantes,
                'fecha_vencimiento': datos['vencimiento'],
                'empresa': datos.get('empresa', ''),
                'notas': datos.get('notas', ''),
                'fecha_generacion': datos.get('generada', '')
            }
            
        except Exception as e:
            return {
                'valida': False,
                'estado': 'INVALIDA',
                'mensaje': f'❌ Licencia inválida: {str(e)}',
                'dias_restantes': 0
            }
    
    def puede_registrar_movimientos(self, codigo_licencia):
        """
        Verifica si se pueden registrar movimientos (licencia vigente)
        """
        info = self.validar_licencia(codigo_licencia)
        return info['valida'] and info['estado'] != 'VENCIDA'
    
    def puede_consultar(self, codigo_licencia):
        """
        Verifica si se puede consultar (siempre permitido, incluso vencida)
        """
        info = self.validar_licencia(codigo_licencia)
        return info['valida']


# ============================================
# FUNCIONES DE USO PARA EL ADMINISTRADOR
# ============================================

def generar_nueva_licencia_anual(empresa=""):
    """
    Genera una licencia con vencimiento en 1 año desde hoy
    USO: Para generar licencias nuevas para clientes
    """
    manager = LicenseManager()
    
    # Vencimiento en 1 año
    fecha_vencimiento = datetime.now() + timedelta(days=365)
    
    # Generar licencia
    licencia = manager.generar_licencia(
        fecha_vencimiento=fecha_vencimiento,
        empresa=empresa,
        notas=f"Licencia anual {datetime.now().year}-{datetime.now().year + 1}"
    )
    
    print("=" * 60)
    print("🔑 NUEVA LICENCIA GENERADA")
    print("=" * 60)
    print(f"Empresa: {empresa if empresa else 'No especificada'}")
    print(f"Vencimiento: {fecha_vencimiento.strftime('%d/%m/%Y')}")
    print(f"\nCÓDIGO DE LICENCIA:")
    print(f"\n{licencia}\n")
    print("=" * 60)
    print("⚠️  GUARDA ESTE CÓDIGO DE FORMA SEGURA")
    print("=" * 60)
    
    return licencia


def validar_licencia_cliente(codigo_licencia):
    """
    Valida una licencia existente
    USO: Para verificar el estado de una licencia
    """
    manager = LicenseManager()
    info = manager.validar_licencia(codigo_licencia)
    
    print("\n" + "=" * 60)
    print("📋 VALIDACIÓN DE LICENCIA")
    print("=" * 60)
    print(f"Estado: {info['estado']}")
    print(f"Mensaje: {info['mensaje']}")
    
    if info['valida']:
        print(f"\nFecha Vencimiento: {info['fecha_vencimiento']}")
        print(f"Días Restantes: {info['dias_restantes']}")
        if info['empresa']:
            print(f"Empresa: {info['empresa']}")
        if info['notas']:
            print(f"Notas: {info['notas']}")
        print(f"Fecha Generación: {info['fecha_generacion']}")
        
        print(f"\n✓ Puede registrar movimientos: {'SÍ' if info['estado'] != 'VENCIDA' else 'NO (Solo consulta)'}")
        print(f"✓ Puede consultar: SÍ")
    else:
        print("\n❌ Licencia inválida - No se puede usar el sistema")
    
    print("=" * 60 + "\n")
    
    return info


# ============================================
# EJEMPLO DE USO EN LA APLICACIÓN
# ============================================

class KardexApp:
    """
    Ejemplo de cómo integrar el sistema de licencias en tu aplicación
    """
    
    def __init__(self):
        self.license_manager = LicenseManager()
        self.codigo_licencia = None
        self.info_licencia = None
    
    def cargar_licencia_guardada(self):
        """
        Cargar licencia desde archivo o base de datos
        En tu app real, esto se guardará en la BD o archivo config
        """
        try:
            with open('licencia.key', 'r') as f:
                self.codigo_licencia = f.read().strip()
            self.info_licencia = self.license_manager.validar_licencia(self.codigo_licencia)
            return True
        except FileNotFoundError:
            return False
    
    def guardar_licencia(self, codigo):
        """
        Guardar licencia ingresada por el usuario
        """
        self.codigo_licencia = codigo
        with open('licencia.key', 'w') as f:
            f.write(codigo)
        self.info_licencia = self.license_manager.validar_licencia(codigo)
    
    def verificar_acceso(self, accion='consultar'):
        """
        Verificar si el usuario puede realizar una acción
        
        Args:
            accion: 'consultar' o 'registrar'
        """
        if not self.codigo_licencia:
            return False, "No hay licencia instalada"
        
        if not self.info_licencia['valida']:
            return False, "Licencia inválida"
        
        if accion == 'consultar':
            return True, "Acceso permitido"
        
        if accion == 'registrar':
            if self.info_licencia['estado'] == 'VENCIDA':
                return False, "Licencia vencida. Solo puede consultar. Contacte al administrador."
            return True, "Acceso permitido"
        
        return False, "Acción no reconocida"
    
    def mostrar_alerta_vencimiento(self):
        """
        Mostrar alerta si la licencia está por vencer (30 días o menos)
        """
        if self.info_licencia and self.info_licencia['estado'] == 'POR_VENCER':
            return True, self.info_licencia['mensaje']
        return False, ""
    
    def inicio_aplicacion(self):
        """
        Lógica al iniciar la aplicación
        """
        if not self.cargar_licencia_guardada():
            print("❌ No se encontró licencia. Solicite una al administrador.")
            return False
        
        if not self.info_licencia['valida']:
            print("❌ Licencia inválida. Contacte al administrador.")
            return False
        
        # Mostrar alerta si está por vencer
        alerta, mensaje = self.mostrar_alerta_vencimiento()
        if alerta:
            print(f"\n{mensaje}\n")
        
        # Si está vencida, solo modo consulta
        if self.info_licencia['estado'] == 'VENCIDA':
            print("⚠️  LICENCIA VENCIDA - Solo puede CONSULTAR")
            print("⚠️  Contacte al administrador para renovar\n")
        
        return True


# ============================================
# PRUEBAS Y EJEMPLOS
# ============================================

if __name__ == "__main__":
    print("\n🔐 SISTEMA DE LICENCIAMIENTO - KARDEX VALORIZADO\n")
    
    # EJEMPLO 1: Generar una nueva licencia
    print("EJEMPLO 1: Generar licencia anual")
    licencia_nueva = generar_nueva_licencia_anual("Empresa Demo SAC")
    
    # EJEMPLO 2: Validar la licencia generada
    print("\n\nEJEMPLO 2: Validar licencia")
    validar_licencia_cliente(licencia_nueva)
    
    # EJEMPLO 3: Generar licencia que vence pronto (para probar alertas)
    print("\nEJEMPLO 3: Licencia que vence en 20 días")
    manager = LicenseManager()
    licencia_pronto = manager.generar_licencia(
        fecha_vencimiento=datetime.now() + timedelta(days=20),
        empresa="Empresa Test",
        notas="Licencia de prueba"
    )
    validar_licencia_cliente(licencia_pronto)
    
    # EJEMPLO 4: Licencia vencida
    print("\nEJEMPLO 4: Licencia vencida")
    licencia_vencida = manager.generar_licencia(
        fecha_vencimiento=datetime.now() - timedelta(days=10),
        empresa="Empresa Vencida",
        notas="Para pruebas"
    )
    validar_licencia_cliente(licencia_vencida)
    
    # EJEMPLO 5: Uso en la aplicación
    print("\nEJEMPLO 5: Integración en la aplicación")
    app = KardexApp()
    app.guardar_licencia(licencia_nueva)
    
    # Verificar acceso para consultar
    puede, mensaje = app.verificar_acceso('consultar')
    print(f"¿Puede consultar? {puede} - {mensaje}")
    
    # Verificar acceso para registrar
    puede, mensaje = app.verificar_acceso('registrar')
    print(f"¿Puede registrar? {puede} - {mensaje}")
    
    print("\n✅ Sistema de licenciamiento listo para integrar")
