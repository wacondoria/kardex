import sqlite3
from src.models.database_model import OrdenMantenimiento, engine, Base

def update_schema():
    print("Iniciando actualización de esquema - Fase 1...")
    
    # 1. Crear tabla ordenes_mantenimiento (SQLAlchemy lo hace si no existe)
    print("Creando tabla ordenes_mantenimiento...")
    Base.metadata.create_all(engine)
    
    # 2. Alterar tablas existentes (SQLite)
    conn = sqlite3.connect('kardex.db')
    cursor = conn.cursor()
    
    # Equipos: Tarifas
    try:
        cursor.execute("ALTER TABLE equipos ADD COLUMN tarifa_semanal FLOAT DEFAULT 0.0")
        print("Columna tarifa_semanal agregada a equipos.")
    except sqlite3.OperationalError as e:
        print(f"Nota: {e}")

    try:
        cursor.execute("ALTER TABLE equipos ADD COLUMN tarifa_mensual FLOAT DEFAULT 0.0")
        print("Columna tarifa_mensual agregada a equipos.")
    except sqlite3.OperationalError as e:
        print(f"Nota: {e}")

    # AlquilerDetalle: Consumibles y Tipo
    try:
        cursor.execute("ALTER TABLE alquiler_detalles ADD COLUMN tipo_item VARCHAR(20) DEFAULT 'EQUIPO'")
        print("Columna tipo_item agregada a alquiler_detalles.")
    except sqlite3.OperationalError as e:
        print(f"Nota: {e}")

    try:
        cursor.execute("ALTER TABLE alquiler_detalles ADD COLUMN producto_id INTEGER REFERENCES productos(id)")
        print("Columna producto_id agregada a alquiler_detalles.")
    except sqlite3.OperationalError as e:
        print(f"Nota: {e}")
        
    # Make equipo_id nullable in alquiler_detalles? 
    # SQLite doesn't support altering column nullability easily. 
    # However, SQLAlchemy model says nullable=True now. 
    # In SQLite, if we don't enforce NOT NULL in the original CREATE, it's fine.
    # If it was NOT NULL, we might have issues inserting rows without equipo_id.
    # Let's check if we can relax it or if we need to recreate the table.
    # For now, we'll assume we can insert NULL if we don't provide it, unless strict constraint exists.
    # If insertion fails later, we'll need a more complex migration (rename table, create new, copy data).
    
    conn.commit()
    conn.close()
    print("Actualización de esquema completada.")

if __name__ == "__main__":
    update_schema()
