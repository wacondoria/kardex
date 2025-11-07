"""
Funciones de Validación reusables para la aplicación.
"""

from models.database_model import obtener_session, AnioContable, EstadoAnio

class AnioCerradoError(Exception):
    """Excepción personalizada para operaciones en años cerrados."""
    pass

def verificar_estado_anio(fecha):
    """
    Verifica si el año de una fecha dada está abierto.
    Lanza AnioCerradoError si el año está cerrado o no existe.

    Args:
        fecha (date): La fecha de la transacción a verificar.
    """
    session = obtener_session()
    try:
        anio_contable = session.query(AnioContable).filter_by(anio=fecha.year).first()

        if not anio_contable:
            raise AnioCerradoError(f"El año {fecha.year} no ha sido creado. No se pueden registrar transacciones.")

        if anio_contable.estado == EstadoAnio.CERRADO:
            raise AnioCerradoError(f"El año {fecha.year} está cerrado. No se pueden registrar ni modificar transacciones.")

        # Si todo está bien, no hace nada

    finally:
        session.close()
