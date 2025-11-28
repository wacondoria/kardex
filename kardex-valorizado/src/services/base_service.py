from sqlalchemy.orm import Session
from models.database_model import obtener_session

class BaseService:
    """
    Clase base para todos los servicios.
    Maneja la sesión de base de datos.
    """
    def __init__(self, session: Session = None):
        self.session = session or obtener_session()

    def close(self):
        """Cierra la sesión si fue creada internamente"""
        if self.session:
            self.session.close()
