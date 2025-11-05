from src.models.database_model import obtener_session, Licencia
from datetime import datetime, timedelta

session = obtener_session()
nueva_licencia = Licencia(
    codigo_licencia="LICENCIA-PRUEBA-2024-2025",
    fecha_vencimiento=(datetime.now() + timedelta(days=365)).date(),
    activa=True
)
session.add(nueva_licencia)
session.commit()
session.close()
print("✓ Licencia instalada")