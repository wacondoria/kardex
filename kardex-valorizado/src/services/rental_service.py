from models.database_model import obtener_session, Alquiler, AlquilerDetalle, EstadoAlquiler
from datetime import date, timedelta

class RentalService:
    def __init__(self, session=None):
        self.session = session or obtener_session()

    def calculate_best_price(self, days, equipo):
        """
        Calcula el mejor precio posible basado en tarifas diaria, semanal y mensual.
        """
        if days <= 0: return 0.0
        
        t_diaria = equipo.tarifa_diaria_referencial
        t_semanal = equipo.tarifa_semanal
        t_mensual = equipo.tarifa_mensual
        
        # 1. Solo Diaria (Base)
        costo_diario = days * t_diaria
        
        # Si no hay tarifas especiales, retornar diario
        if t_semanal <= 0 and t_mensual <= 0:
            return costo_diario
            
        # 2. Lógica Semanal
        costo_semanal = float('inf')
        if t_semanal > 0:
            weeks = days // 7
            extra_days = days % 7
            
            # Opción A: Semanas completas + días extra
            opcion_a = (weeks * t_semanal) + (extra_days * t_diaria)
            
            # Opción B: Semanas completas + 1 semana (si días extra salen más caros que la semana)
            opcion_b = (weeks + 1) * t_semanal
            
            costo_semanal = min(opcion_a, opcion_b)
            
        # 3. Lógica Mensual
        costo_mensual = float('inf')
        if t_mensual > 0:
            months = days // 30
            extra_days_m = days % 30
            
            # Calcular costo de los días extra usando la mejor opción (diaria o semanal)
            # Recursividad limitada o lógica lineal
            costo_extra = 0
            if extra_days_m > 0:
                # Calcular costo extra como si fuera un alquiler corto
                # Reusamos lógica semanal para estos días extra
                c_dia = extra_days_m * t_diaria
                c_sem = float('inf')
                if t_semanal > 0:
                    w = extra_days_m // 7
                    d = extra_days_m % 7
                    c_sem = min((w * t_semanal) + (d * t_diaria), (w + 1) * t_semanal)
                costo_extra = min(c_dia, c_sem)
            
            # Opción A: Meses + extra optimizado
            opcion_a_m = (months * t_mensual) + costo_extra
            
            # Opción B: Meses + 1 mes
            opcion_b_m = (months + 1) * t_mensual
            
            costo_mensual = min(opcion_a_m, opcion_b_m)
            
        return min(costo_diario, costo_semanal, costo_mensual)

    def get_pending_billing(self, start_date: date, end_date: date):
        """
        Calcula los montos a facturar para alquileres activos en el rango de fechas dado.
        Retorna una lista de diccionarios con el detalle del cálculo.
        """
        results = []
        
        alquileres = self.session.query(Alquiler).filter(
            Alquiler.estado.in_([EstadoAlquiler.ACTIVO, EstadoAlquiler.FINALIZADO]),
            Alquiler.fecha_inicio <= end_date
        ).all()
        
        for alquiler in alquileres:
            for detalle in alquiler.detalles:
                # Ignorar consumibles para facturación por tiempo (se cobran una vez)
                # Asumimos que consumibles tienen tipo_item='CONSUMIBLE' o equipo_id es NULL
                if hasattr(detalle, 'tipo_item') and detalle.tipo_item.value == 'CONSUMIBLE':
                    continue
                if not detalle.equipo:
                    continue

                # Fecha inicio del cobro para este ítem
                item_start = detalle.fecha_salida.date() if detalle.fecha_salida else alquiler.fecha_inicio
                
                # Fecha fin del cobro para este ítem
                item_end = None
                if detalle.fecha_retorno:
                    item_end = detalle.fecha_retorno.date()
                elif alquiler.estado == EstadoAlquiler.FINALIZADO:
                    item_end = alquiler.fecha_fin_estimada # Fallback
                else:
                    item_end = end_date # Sigue activo
                
                # Intersección con el periodo de facturación
                billing_start = max(item_start, start_date)
                billing_end = min(item_end, end_date) if item_end else end_date
                
                if billing_start <= billing_end:
                    days = (billing_end - billing_start).days + 1
                    if days > 0:
                        # Usar lógica de mejor precio
                        amount = self.calculate_best_price(days, detalle.equipo)
                        
                        # Si el precio unitario pactado en el detalle es diferente al de lista,
                        # podríamos tener que respetar el pactado.
                        # PERO, la lógica de "Best Price" suele ser para tarifas de lista.
                        # Si el contrato fijó una tarifa diaria, ¿se debe optimizar?
                        # Asumiremos que si el contrato tiene tarifa, se usa esa tarifa * dias.
                        # La optimización es útil para cotizar o si el contrato es "Tarifa Variable".
                        # Para este requerimiento, el usuario pidió "Gestión de Tarifas", así que lo aplicamos.
                        # Sin embargo, si ya se pactó un precio, cambiarlo puede ser delicado.
                        # Vamos a mostrar el cálculo optimizado como sugerencia o usarlo si el precio es 0.
                        
                        # ESTRATEGIA: Si el precio unitario coincide con la tarifa diaria referencial, aplicamos optimización.
                        # Si es diferente (descuento manual), respetamos el lineal.
                        
                        if abs(detalle.precio_unitario - detalle.equipo.tarifa_diaria_referencial) < 0.01:
                             total_final = amount
                             tarifa_aplicada = amount / days # Promedio diario
                        else:
                             total_final = days * detalle.precio_unitario
                             tarifa_aplicada = detalle.precio_unitario

                        results.append({
                            'alquiler_id': alquiler.id,
                            'cliente': alquiler.cliente.razon_social_o_nombre,
                            'equipo': detalle.equipo.nombre,
                            'codigo_equipo': detalle.equipo.codigo,
                            'periodo_inicio': billing_start,
                            'periodo_fin': billing_end,
                            'dias': days,
                            'tarifa': tarifa_aplicada,
                            'total': total_final
                        })
                        
        return results

    def close(self):
        self.session.close()
