from datetime import date, timedelta
import sys
from pathlib import Path
from sqlalchemy import inspect

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.database_model import obtener_session, Licencia, engine

def activate_license():
    # Ensure table exists
    inspector = inspect(engine)
    if not inspector.has_table('licencias'):
        print("Table 'licencias' not found. Creating it...")
        Licencia.__table__.create(engine)
        print("Table 'licencias' created.")

    session = obtener_session()
    try:
        # Deactivate existing licenses
        existing_licenses = session.query(Licencia).filter_by(activa=True).all()
        for license in existing_licenses:
            license.activa = False
            print(f"Deactivated existing license ID: {license.id}")
        
        # Create new license
        new_license = Licencia(
            clave="LICENSE-KEY-12345",
            fecha_inicio=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=365),
            activa=True,
            tipo="STANDARD"
        )
        session.add(new_license)
        session.commit()
        print(f"Successfully activated new license. Valid until: {new_license.fecha_vencimiento}")
        
    except Exception as e:
        session.rollback()
        print(f"Error activating license: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    activate_license()
