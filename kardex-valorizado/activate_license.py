import sys
from pathlib import Path
from datetime import datetime, timedelta

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.database_model import obtener_session, Licencia
from license_system import LicenseManager

def activar_licencia():
    print("🔐 Iniciando activación de licencia...")
    
    session = obtener_session()
    manager = LicenseManager()
    
    try:
        # 1. Generar nueva licencia válida por 1 año
        fecha_vencimiento = datetime.now() + timedelta(days=365)
        codigo_licencia = manager.generar_licencia(
            fecha_vencimiento=fecha_vencimiento,
            empresa="Usuario Registrado",
            notas="Licencia activada automáticamente"
        )
        
        print(f"✓ Licencia generada correctamente.")
        print(f"  Vence: {fecha_vencimiento.strftime('%d/%m/%Y')}")
        
        # 2. Desactivar licencias anteriores
        licencias_activas = session.query(Licencia).filter_by(activa=True).all()
        for lic in licencias_activas:
            lic.activa = False
            print(f"  - Licencia anterior desactivada (ID: {lic.id})")
        
        # 3. Insertar nueva licencia
        nueva_licencia = Licencia(
            codigo_licencia=codigo_licencia,
            fecha_vencimiento=fecha_vencimiento.date(),
            activa=True,
            fecha_instalacion=datetime.now()
        )
        
        session.add(nueva_licencia)
        session.commit()
        
        print("\n✨ ¡LICENCIA ACTIVADA CON ÉXITO! ✨")
        print("El sistema ahora está plenamente operativo.")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error al activar licencia: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    activar_licencia()
