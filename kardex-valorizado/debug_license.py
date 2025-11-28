from license_system import LicenseManager
from cryptography.fernet import Fernet
import base64

try:
    print("Testing LicenseManager...")
    manager = LicenseManager()
    print("LicenseManager instantiated.")
    
    print("Testing encryption...")
    lic = manager.generar_licencia(fecha_vencimiento=None, empresa="Test") # fecha_vencimiento will fail if None, but let's see where it fails
    print(f"License generated: {lic}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
