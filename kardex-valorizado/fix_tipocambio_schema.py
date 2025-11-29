import sys
from pathlib import Path
import sqlalchemy

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.database_model import Base, TipoCambio, engine

def fix_schema():
    print("Connecting to database...")
    # engine is already created on import
    
    print("Dropping 'tipo_cambio' table...")
    try:
        TipoCambio.__table__.drop(engine)
        print("Table dropped.")
    except Exception as e:
        print(f"Warning dropping table: {e}")

    print("Recreating 'tipo_cambio' table...")
    try:
        TipoCambio.__table__.create(engine)
        print("Table recreated successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")

if __name__ == "__main__":
    fix_schema()
