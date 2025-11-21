"""
Configuración centralizada del sistema Kardex Valorizado.
"""
import os
from decimal import Decimal

# Configuración de Base de Datos
DB_NAME = "kardex.db"
DB_URL = f"sqlite:///{DB_NAME}"

# Configuración de Impuestos
IGV_PORCENTAJE = Decimal('0.18')
IGV_FACTOR = Decimal('1.18')

# Rutas de Archivos (Ejemplo)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

# Formatos
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"

# Monedas
MONEDA_SOLES = "SOLES"
MONEDA_DOLARES = "DOLARES"
SIMBOLO_SOLES = "S/"
SIMBOLO_DOLARES = "$"
