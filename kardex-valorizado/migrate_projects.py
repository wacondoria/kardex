import sqlite3
from src.utils.config import Config

def migrate():
    print("--- Starting Migration: Projects Module ---")
    
    try:
        db_url = Config.get_db_url()
        db_path = db_url.replace('sqlite:///', '')
    except:
        db_path = 'kardex.db'

    print(f"Target Database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Create table 'proyectos'
    print("1. Creating table 'proyectos'...")
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            cliente_id INTEGER NOT NULL,
            codigo VARCHAR(50) NOT NULL UNIQUE,
            nombre VARCHAR(200) NOT NULL,
            ubicacion VARCHAR(200),
            descripcion TEXT,
            fecha_inicio DATE NOT NULL,
            fecha_fin_estimada DATE,
            fecha_fin_real DATE,
            presupuesto_estimado FLOAT DEFAULT 0.0,
            estado VARCHAR(20) DEFAULT 'PLANIFICACION',
            activo BOOLEAN DEFAULT 1,
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(empresa_id) REFERENCES empresas(id),
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        );
        """)
        print("   -> Table 'proyectos' created (or already exists).")
    except Exception as e:
        print(f"   -> Error creating table: {e}")

    # 2. Add 'proyecto_id' to 'alquileres'
    print("2. Adding 'proyecto_id' to 'alquileres'...")
    try:
        cursor.execute("ALTER TABLE alquileres ADD COLUMN proyecto_id INTEGER REFERENCES proyectos(id);")
        print("   -> Column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("   -> Column already exists.")
        else:
            print(f"   -> Error: {e}")

    # 3. Add 'proyecto_id' to 'ventas'
    print("3. Adding 'proyecto_id' to 'ventas'...")
    try:
        cursor.execute("ALTER TABLE ventas ADD COLUMN proyecto_id INTEGER REFERENCES proyectos(id);")
        print("   -> Column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("   -> Column already exists.")
        else:
            print(f"   -> Error: {e}")

    # 4. Add 'proyecto_id' to 'requisiciones'
    print("4. Adding 'proyecto_id' to 'requisiciones'...")
    try:
        cursor.execute("ALTER TABLE requisiciones ADD COLUMN proyecto_id INTEGER REFERENCES proyectos(id);")
        print("   -> Column added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("   -> Column already exists.")
        else:
            print(f"   -> Error: {e}")

    conn.commit()
    conn.close()
    print("--- Migration Completed Successfully ---")

if __name__ == "__main__":
    migrate()
