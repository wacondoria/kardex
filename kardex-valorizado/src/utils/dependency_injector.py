from sqlalchemy.orm import Session
from models.database_model import obtener_session
from services.inventory_service import InventoryService
from services.audit_service import AuditService

class ServiceContainer:
    """
    Contenedor de Inyección de Dependencias simple.
    Gestiona la creación de servicios y sus dependencias (sesiones, config, etc).
    """
    
    def __init__(self):
        self._session = None
        self._inventory_service = None
        self._audit_service = None

    @property
    def session(self) -> Session:
        """Obtiene o crea una sesión de base de datos compartida para este ámbito."""
        if self._session is None:
            self._session = obtener_session()
        return self._session

    def get_inventory_service(self) -> InventoryService:
        """Retorna una instancia de InventoryService."""
        if self._inventory_service is None:
            self._inventory_service = InventoryService(self.session)
        return self._inventory_service

    def get_audit_service(self) -> AuditService:
        """Retorna la clase AuditService (es estática por ahora) o una instancia si se refactoriza."""
        return AuditService

    def close_session(self):
        """Cierra la sesión de base de datos si está abierta."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_session()
