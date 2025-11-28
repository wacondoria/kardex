from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextmanager
def transaction(session: Session):
    """
    Context manager para transacciones atómicas.
    Maneja commit y rollback automáticamente.
    
    Uso:
    with transaction(session):
        session.add(obj)
        # ... otras operaciones
    """
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error de base de datos en transacción: {str(e)}")
        raise e
    except Exception as e:
        session.rollback()
        logger.error(f"Error inesperado en transacción: {str(e)}")
        raise e
