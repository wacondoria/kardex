from models.database_model import obtener_session, Alquiler, AlquilerDetalle, EstadoAlquiler
from datetime import date, timedelta

class RentalService:
    def __init__(self, session=None):
        self.session = session or obtener_session()

    def get_pending_billing(self, start_date: date, end_date: date):
        """
        Calcula los montos a facturar para alquileres activos en el rango de fechas dado.
        Retorna una lista de diccionarios con el detalle del cálculo.
        """
        results = []
        
        # Buscar alquileres que estén activos o finalizados pero que se superpongan con el rango
        # Filtro básico: fecha_inicio <= end_date AND (fecha_fin_real IS NULL OR fecha_fin_real >= start_date)
        # Nota: fecha_fin_real no existe explícitamente en el modelo actual como columna simple, 
        # usamos fecha_fin_estimada o el estado. Para facturación precisa, deberíamos tener fecha de devolución real.
        # Asumiremos que si está ACTIVO, sigue corriendo. Si está FINALIZADO, usamos la fecha de retorno del detalle (max).
        
        alquileres = self.session.query(Alquiler).filter(
            Alquiler.estado.in_([EstadoAlquiler.ACTIVO, EstadoAlquiler.FINALIZADO]),
            Alquiler.fecha_inicio <= end_date
        ).all()
        
        for alquiler in alquileres:
            # Determinar fin efectivo del alquiler para este cálculo
            # Si está activo, el fin es infinito (o hasta end_date)
            # Si está finalizado, necesitamos saber cuándo terminó realmente.
            # Por simplicidad, iteramos detalles.
            
            for detalle in alquiler.detalles:
                # Fecha inicio del cobro para este ítem
                item_start = detalle.fecha_salida.date() if detalle.fecha_salida else alquiler.fecha_inicio
                
                # Fecha fin del cobro para este ítem
                item_end = None
                if detalle.fecha_retorno:
                    item_end = detalle.fecha_retorno.date()
                elif alquiler.estado == EstadoAlquiler.FINALIZADO:
                    # Fallback si no tiene fecha retorno detalle pero alquiler cerró
                    item_end = alquiler.fecha_fin_estimada # O fecha actual? Mejor estimar.
                else:
                    # Sigue activo
                    item_end = end_date # Se cobra hasta el fin del periodo de facturación
                
                # Intersección con el periodo de facturación
                billing_start = max(item_start, start_date)
                billing_end = min(item_end, end_date) if item_end else end_date
                
                if billing_start <= billing_end:
                    days = (billing_end - billing_start).days + 1
                    if days > 0:
                        amount = days * detalle.precio_unitario
                        
                        results.append({
                            'alquiler_id': alquiler.id,
                            'cliente': alquiler.cliente.razon_social_o_nombre,
                            'equipo': detalle.equipo.nombre,
                            'codigo_equipo': detalle.equipo.codigo,
                            'periodo_inicio': billing_start,
                            'periodo_fin': billing_end,
                            'dias': days,
                            'tarifa': detalle.precio_unitario,
                            'total': amount
                        })
                        
        return results

    def close(self):
        self.session.close()
