import sys
import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError

# Añadir el directorio 'src' al path para poder importar los modelos
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# --- Definición del Modelo AnioContable ---
# Se replica aquí para que el script sea autocontenido y no dependa de la importación directa
# de la app, simplificando su ejecución.
Base = declarative_base()

class AnioContable(Base):
    __tablename__ = 'anio_contable'
    id = Column(Integer, primary_key=True)
    anio = Column(Integer, unique=True, nullable=False)
    estado = Column(String, default='Abierto', nullable=False) # Abierto, Cerrado
    bloqueado = Column(Boolean, default=False, nullable=False)

# --- Lógica del Script ---
def agregar_anio_inicial():
    """
    Asegura que exista al menos un año contable abierto en la base de datos
    para permitir el inicio de sesión inicial.
    """
    db_path = os.path.join(project_root, 'kardex.db')
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Verificar si la tabla existe, si no, crearla.
        Base.metadata.create_all(engine)

        # Verificar si ya existe el año 2025
        anio_2025 = session.query(AnioContable).filter_by(anio=2025).first()

        if anio_2025:
            print("El año 2025 ya existe en la base de datos.")
            # Si existe pero no está abierto, se abre.
            if anio_2025.estado != 'Abierto':
                anio_2025.estado = 'Abierto'
                anio_2025.bloqueado = False
                session.commit()
                print("El año 2025 ha sido reabierto.")
        else:
            # Si no existe, crearlo
            nuevo_anio = AnioContable(anio=2025, estado='Abierto', bloqueado=False)
            session.add(nuevo_anio)
            session.commit()
            print("Se ha creado y abierto el año contable 2025.")

    except IntegrityError:
        session.rollback()
        print("Error de integridad. Es posible que el año ya existiera.")
    except Exception as e:
        session.rollback()
        print(f"Ocurrió un error inesperado: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    agregar_anio_inicial()
