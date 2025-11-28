from models.database_model import Auditoria
from sqlalchemy.orm import Session
import json
import traceback

class AuditService:
    """
    Servicio para registrar auditoría de acciones de usuarios.
    """

    @staticmethod
    def log_action(session: Session, usuario_id: int, accion: str, tabla: str = None, 
                   registro_id: int = None, detalles: dict = None, ip_address: str = None):
        """
        Registra una acción en la tabla de auditoría.
        
        Args:
            session: Sesión de base de datos
            usuario_id: ID del usuario que realiza la acción
            accion: Tipo de acción (CREATE, UPDATE, DELETE, LOGIN, etc.)
            tabla: Nombre de la tabla afectada (opcional)
            registro_id: ID del registro afectado (opcional)
            detalles: Diccionario con detalles de los cambios (opcional)
            ip_address: Dirección IP del usuario (opcional)
        """
        try:
            detalles_str = None
            if detalles:
                try:
                    detalles_str = json.dumps(detalles, default=str)
                except Exception:
                    detalles_str = str(detalles)

            audit_entry = Auditoria(
                usuario_id=usuario_id,
                accion=accion,
                tabla=tabla,
                registro_id=registro_id,
                detalles=detalles_str,
                ip_address=ip_address
            )
            
            session.add(audit_entry)
            # No hacemos commit aquí para que sea parte de la transacción principal si existe.
            # Pero si queremos que el log persista incluso si la operación falla, deberíamos usar una sesión separada.
            # Por ahora, asumiremos que es parte de la transacción de negocio.
            
        except Exception as e:
            print(f"Error al registrar auditoría: {e}")
            traceback.print_exc()
