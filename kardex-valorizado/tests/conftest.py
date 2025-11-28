import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from models.database_model import Base, Producto, Categoria, Almacen, Empresa, MovimientoStock, TipoMovimiento

@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def session(engine):
    """Create a new database session for a test"""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def sample_data(session):
    """Create sample data for tests"""
    # Empresa
    empresa = Empresa(ruc="20123456789", razon_social="Test Company")
    session.add(empresa)
    session.flush()

    # Almacen
    almacen = Almacen(empresa_id=empresa.id, codigo="ALM01", nombre="Almacen Principal")
    session.add(almacen)
    session.flush()

    # Categoria
    categoria = Categoria(nombre="Test Category")
    session.add(categoria)
    session.flush()

    # Producto
    producto = Producto(
        codigo="TEST0-000001",
        nombre="Test Product",
        categoria_id=categoria.id,
        unidad_medida="UND",
        stock_minimo=10.0
    )
    session.add(producto)
    session.flush()

    return {
        "empresa": empresa,
        "almacen": almacen,
        "categoria": categoria,
        "producto": producto
    }
