from sqlalchemy import create_engine, text, inspect
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.database_model import Base

DB_URL = 'sqlite:///kardex.db'

def fix_schema():
    engine = create_engine(DB_URL)
    inspector = inspect(engine)
    
    with engine.connect() as connection:
        # 1. Fix Proyectos table
        if 'proyectos' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('proyectos')]
            if 'costo_real' not in columns:
                print("Adding 'costo_real' to 'proyectos' table...")
                connection.execute(text("ALTER TABLE proyectos ADD COLUMN costo_real FLOAT DEFAULT 0.0"))
                print("Done.")
            else:
                print("'costo_real' already exists in 'proyectos'.")

        # 2. Fix Requisiciones table
        if 'requisiciones' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('requisiciones')]
            if 'solicitante_id' not in columns:
                print("Adding 'solicitante_id' to 'requisiciones' table...")
                # SQLite doesn't support adding NOT NULL columns without default value easily, 
                # but we can add it as nullable first or with default.
                # Assuming we have a default user or we allow null temporarily.
                # Ideally we should link to an existing user.
                # For now, let's make it nullable to avoid errors, or default to 1 (admin).
                connection.execute(text("ALTER TABLE requisiciones ADD COLUMN solicitante_id INTEGER DEFAULT 1 REFERENCES usuarios(id)"))
                print("Done.")
            else:
                print("'solicitante_id' already exists in 'requisiciones'.")

            if 'fecha_requerida' not in columns:
                print("Adding 'fecha_requerida' to 'requisiciones' table...")
                connection.execute(text("ALTER TABLE requisiciones ADD COLUMN fecha_requerida DATE"))
                print("Done.")

            if 'numero_requisicion' not in columns:
                print("Adding 'numero_requisicion' to 'requisiciones' table...")
                connection.execute(text("ALTER TABLE requisiciones ADD COLUMN numero_requisicion VARCHAR(20) DEFAULT 'REQ-000'"))
                print("Done.")

            if 'observaciones' not in columns:
                print("Adding 'observaciones' to 'requisiciones' table...")
                connection.execute(text("ALTER TABLE requisiciones ADD COLUMN observaciones TEXT"))
                print("Done.")

            if 'estado' not in columns:
                print("Adding 'estado' to 'requisiciones' table...")
                connection.execute(text("ALTER TABLE requisiciones ADD COLUMN estado VARCHAR(20) DEFAULT 'PENDIENTE'"))
                print("Done.")

        # 3. Fix Empresas table
        if 'empresas' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('empresas')]
            if 'activo' not in columns:
                print("Adding 'activo' to 'empresas' table...")
                connection.execute(text("ALTER TABLE empresas ADD COLUMN activo BOOLEAN DEFAULT 1"))
                print("Done.")
            else:
                print("'activo' already exists in 'empresas'.")

        # 4. Fix Alquileres table
        if 'alquileres' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('alquileres')]
            if 'numero_contrato' not in columns:
                print("Adding 'numero_contrato' to 'alquileres' table...")
                connection.execute(text("ALTER TABLE alquileres ADD COLUMN numero_contrato VARCHAR(20) DEFAULT 'PENDING-000'"))
                print("Done.")
            
            if 'fecha_fin_real' not in columns:
                print("Adding 'fecha_fin_real' to 'alquileres' table...")
                connection.execute(text("ALTER TABLE alquileres ADD COLUMN fecha_fin_real DATE"))
                print("Done.")

            if 'moneda' not in columns:
                print("Adding 'moneda' to 'alquileres' table...")
                connection.execute(text("ALTER TABLE alquileres ADD COLUMN moneda VARCHAR(10) DEFAULT 'SOLES'"))
                print("Done.")

            if 'tipo_cambio' not in columns:
                print("Adding 'tipo_cambio' to 'alquileres' table...")
                connection.execute(text("ALTER TABLE alquileres ADD COLUMN tipo_cambio FLOAT DEFAULT 1.0"))
                print("Done.")

            if 'subtotal' not in columns:
                print("Adding 'subtotal' to 'alquileres' table...")
                connection.execute(text("ALTER TABLE alquileres ADD COLUMN subtotal FLOAT DEFAULT 0.0"))
                print("Done.")

            if 'igv' not in columns:
                print("Adding 'igv' to 'alquileres' table...")
                connection.execute(text("ALTER TABLE alquileres ADD COLUMN igv FLOAT DEFAULT 0.0"))
                print("Done.")

            if 'total' not in columns:
                print("Adding 'total' to 'alquileres' table...")
                connection.execute(text("ALTER TABLE alquileres ADD COLUMN total FLOAT DEFAULT 0.0"))
                print("Done.")
            
            if 'observaciones' not in columns:
                print("Adding 'observaciones' to 'alquileres' table...")
                connection.execute(text("ALTER TABLE alquileres ADD COLUMN observaciones TEXT"))
                print("Done.")

        # 5. Fix Clientes table
        if 'clientes' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('clientes')]
            if 'tipo_documento' not in columns:
                print("Adding 'tipo_documento' to 'clientes' table...")
                connection.execute(text("ALTER TABLE clientes ADD COLUMN tipo_documento VARCHAR(20) DEFAULT 'RUC'"))
                print("Done.")
            else:
                print("'tipo_documento' already exists in 'clientes'.")

        # 6. Fix Ventas table
        if 'ventas' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('ventas')]
            if 'fecha_registro_contable' not in columns:
                print("Adding 'fecha_registro_contable' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN fecha_registro_contable DATE"))
                print("Done.")
            else:
                print("'fecha_registro_contable' already exists in 'ventas'.")

            if 'numero_documento' not in columns:
                print("Adding 'numero_documento' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN numero_documento VARCHAR(20) DEFAULT 'PENDING-000'"))
                print("Done.")

            if 'numero_proceso' not in columns:
                print("Adding 'numero_proceso' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN numero_proceso VARCHAR(20)"))
                print("Done.")

            if 'tipo_documento' not in columns:
                print("Adding 'tipo_documento' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN tipo_documento VARCHAR(20) DEFAULT 'FACTURA'"))
                print("Done.")

            if 'moneda' not in columns:
                print("Adding 'moneda' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN moneda VARCHAR(10) DEFAULT 'SOLES'"))
                print("Done.")

            if 'tipo_cambio' not in columns:
                print("Adding 'tipo_cambio' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN tipo_cambio FLOAT DEFAULT 1.0"))
                print("Done.")

            if 'incluye_igv' not in columns:
                print("Adding 'incluye_igv' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN incluye_igv BOOLEAN DEFAULT 0"))
                print("Done.")

            if 'igv_porcentaje' not in columns:
                print("Adding 'igv_porcentaje' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN igv_porcentaje FLOAT DEFAULT 18.0"))
                print("Done.")

            if 'subtotal' not in columns:
                print("Adding 'subtotal' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN subtotal FLOAT DEFAULT 0.0"))
                print("Done.")

            if 'igv' not in columns:
                print("Adding 'igv' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN igv FLOAT DEFAULT 0.0"))
                print("Done.")

            if 'total' not in columns:
                print("Adding 'total' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN total FLOAT DEFAULT 0.0"))
                print("Done.")

            if 'observaciones' not in columns:
                print("Adding 'observaciones' to 'ventas' table...")
                connection.execute(text("ALTER TABLE ventas ADD COLUMN observaciones TEXT"))
                print("Done.")
        
        connection.commit()

if __name__ == "__main__":
    fix_schema()
