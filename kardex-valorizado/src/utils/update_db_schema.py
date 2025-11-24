import sys
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_URL
from models.database_model import Base, TipoEquipo, Equipo

def update_schema():
    print(f"Connecting to database: {DB_URL}")
    engine = create_engine(DB_URL)
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # 1. Create tipos_equipo table if not exists
        if not inspector.has_table("tipos_equipo"):
            print("Creating table 'tipos_equipo'...")
            TipoEquipo.__table__.create(engine)
            
            # Insert default types
            print("Inserting default types...")
            conn.execute(text("INSERT INTO tipos_equipo (nombre, descripcion) VALUES ('MAQUINARIA PESADA', 'Equipos grandes de movimiento de tierra')"))
            conn.execute(text("INSERT INTO tipos_equipo (nombre, descripcion) VALUES ('HERRAMIENTAS ELECTRICAS', 'Taladros, amoladoras, etc.')"))
            conn.execute(text("INSERT INTO tipos_equipo (nombre, descripcion) VALUES ('EQUIPOS DE MEDICION', 'Niveles, teodolitos, etc.')"))
            conn.execute(text("INSERT INTO tipos_equipo (nombre, descripcion) VALUES ('ANDAMIOS Y ENCOFRADOS', 'Estructuras temporales')"))
            conn.execute(text("INSERT INTO tipos_equipo (nombre, descripcion) VALUES ('GENERADORES', 'Grupos electrógenos')"))
            conn.commit()
        else:
            print("Table 'tipos_equipo' already exists.")

        # 2. Add columns to equipos table
        columns = [col['name'] for col in inspector.get_columns("equipos")]
        
        if "tipo_equipo_id" not in columns:
            print("Adding column 'tipo_equipo_id' to 'equipos'...")
            conn.execute(text("ALTER TABLE equipos ADD COLUMN tipo_equipo_id INTEGER REFERENCES tipos_equipo(id)"))
            conn.commit()
        
        if "capacidad" not in columns:
            print("Adding column 'capacidad' to 'equipos'...")
            conn.execute(text("ALTER TABLE equipos ADD COLUMN capacidad VARCHAR(100)"))
            conn.commit()

        if "serie_modelo" not in columns:
            print("Adding column 'serie_modelo' to 'equipos'...")
            conn.execute(text("ALTER TABLE equipos ADD COLUMN serie_modelo VARCHAR(100)"))
            conn.commit()

        if "tarifa_diaria_dolares" not in columns:
            print("Adding column 'tarifa_diaria_dolares' to 'equipos'...")
            conn.execute(text("ALTER TABLE equipos ADD COLUMN tarifa_diaria_dolares FLOAT DEFAULT 0.0"))
            conn.commit()
            
    print("Schema update completed successfully.")

if __name__ == "__main__":
    try:
        update_schema()
    except Exception as e:
        print(f"Error updating schema: {e}")
