"""
KardexManager - Lógica de negocio centralizada para la gestión de inventario.
Archivo: src/utils/kardex_manager.py
"""

from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm.session import Session
from models.database_model import MovimientoStock, TipoMovimiento, Empresa

class KardexManager:
    """
    Gestiona toda la lógica de negocio relacionada con el Kardex, incluyendo movimientos de stock,
    cálculos de costos y recálculos.
    """

    def __init__(self, session: Session):
        self.session = session

    def recalcular_kardex_posterior(self, producto_almacen_afectados: set, fecha_referencia):
        """
        Recalcula los saldos y costos del Kardex para productos/almacenes específicos
        a partir de una fecha dada. Asume Costo Promedio Ponderado.
        """
        print(f"DEBUG: Iniciando recálculo de Kardex para {len(producto_almacen_afectados)} pares desde {fecha_referencia}")
        DOS_DECIMALES = Decimal('0.01')
        SEIS_DECIMALES = Decimal('0.000001')

        for prod_id, alm_id in producto_almacen_afectados:
            print(f"DEBUG: Recalculando para Producto ID: {prod_id}, Almacén ID: {alm_id}")

            mov_anterior = self.session.query(MovimientoStock).filter(
                MovimientoStock.producto_id == prod_id,
                MovimientoStock.almacen_id == alm_id,
                MovimientoStock.fecha_documento < fecha_referencia
            ).order_by(MovimientoStock.fecha_documento.desc(), MovimientoStock.id.desc()).first()

            saldo_cant_actual = Decimal(str(mov_anterior.saldo_cantidad)) if mov_anterior else Decimal('0')
            saldo_costo_actual = Decimal(str(mov_anterior.saldo_costo_total)) if mov_anterior else Decimal('0')
            print(f"DEBUG: Saldos iniciales - Cant: {saldo_cant_actual}, Costo Total: {saldo_costo_actual}")

            movimientos_a_recalcular = self.session.query(MovimientoStock).filter(
                MovimientoStock.producto_id == prod_id,
                MovimientoStock.almacen_id == alm_id,
                MovimientoStock.fecha_documento >= fecha_referencia
            ).order_by(MovimientoStock.fecha_documento.asc(), MovimientoStock.id.asc()).all()

            if not movimientos_a_recalcular:
                print(f"DEBUG: No hay movimientos posteriores para recalcular.")
                continue

            for mov in movimientos_a_recalcular:
                cant_entrada = Decimal(str(mov.cantidad_entrada))
                cant_salida = Decimal(str(mov.cantidad_salida))
                costo_total_movimiento = Decimal(str(mov.costo_total))

                costo_promedio_anterior = Decimal('0')
                if saldo_cant_actual > 0:
                    costo_promedio_anterior = (saldo_costo_actual / saldo_cant_actual).quantize(SEIS_DECIMALES, rounding=ROUND_HALF_UP)

                if cant_salida > 0:
                    costo_unitario_salida = costo_promedio_anterior
                    costo_total_salida = (cant_salida * costo_unitario_salida).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

                    mov.costo_unitario = float(costo_unitario_salida)
                    mov.costo_total = float(costo_total_salida)
                    costo_total_movimiento = -costo_total_salida

                elif cant_entrada > 0:
                    costo_total_movimiento = Decimal(str(mov.costo_total))
                else:
                    costo_total_movimiento = Decimal('0')

                saldo_cant_actual += cant_entrada - cant_salida
                saldo_costo_actual += costo_total_movimiento

                if saldo_cant_actual <= 0:
                    saldo_costo_actual = Decimal('0')
                    saldo_cant_actual = Decimal('0')

                mov.saldo_cantidad = float(saldo_cant_actual.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP))
                mov.saldo_costo_total = float(saldo_costo_actual.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP))

            print(f"DEBUG: Recálculo completado para Producto ID: {prod_id}, Almacén ID: {alm_id}")

        print(f"DEBUG: Recálculo de Kardex finalizado.")

    def registrar_movimiento(self, *, empresa_id, producto_id, almacen_id, tipo,
                             cantidad_entrada, cantidad_salida, costo_unitario,
                             costo_total, numero_documento, fecha_documento,
                             destino_id=None, observaciones=""):
        """
        Busca el último saldo, calcula el nuevo y registra un movimiento de stock.
        """
        ultimo_mov = self.session.query(MovimientoStock).filter_by(
            empresa_id=empresa_id,
            producto_id=producto_id,
            almacen_id=almacen_id
        ).order_by(MovimientoStock.id.desc()).first()

        saldo_anterior_cant = Decimal(str(ultimo_mov.saldo_cantidad)) if ultimo_mov else Decimal('0')
        saldo_anterior_costo = Decimal(str(ultimo_mov.saldo_costo_total)) if ultimo_mov else Decimal('0')

        # Calcular nuevo saldo de cantidad
        nuevo_saldo_cant = saldo_anterior_cant + Decimal(str(cantidad_entrada)) - Decimal(str(cantidad_salida))

        # Calcular nuevo saldo de costo
        nuevo_saldo_costo = saldo_anterior_costo
        if cantidad_entrada > 0:
            nuevo_saldo_costo += Decimal(str(costo_total))
        elif cantidad_salida > 0:
            nuevo_saldo_costo -= Decimal(str(costo_total))

        # Crear la instancia del movimiento
        movimiento = MovimientoStock(
            empresa_id=empresa_id,
            producto_id=producto_id,
            almacen_id=almacen_id,
            tipo=tipo,
            numero_documento=numero_documento,
            fecha_documento=fecha_documento,
            destino_id=destino_id,
            cantidad_entrada=float(cantidad_entrada),
            cantidad_salida=float(cantidad_salida),
            costo_unitario=float(costo_unitario),
            costo_total=float(costo_total),
            saldo_cantidad=float(nuevo_saldo_cant),
            saldo_costo_total=float(nuevo_saldo_costo),
            observaciones=observaciones
        )
        self.session.add(movimiento)

    def calcular_costo_salida(self, empresa_id, producto_id, almacen_id, cantidad):
        """
        Calcula el costo de los bienes vendidos según el método de valuación.
        Retorna (costo_unitario, costo_total)
        """
        # Para simplificar, usamos promedio ponderado.
        # En producción, se deberían implementar los 3 métodos.
        ultimo_mov = self.session.query(MovimientoStock).filter_by(
            empresa_id=empresa_id,
            producto_id=producto_id,
            almacen_id=almacen_id
        ).order_by(MovimientoStock.id.desc()).first()

        if ultimo_mov and ultimo_mov.saldo_cantidad > 0:
            costo_unitario = Decimal(str(ultimo_mov.saldo_costo_total)) / Decimal(str(ultimo_mov.saldo_cantidad))
        else:
            costo_unitario = Decimal('0')

        costo_total = costo_unitario * Decimal(str(cantidad))

        return float(costo_unitario), float(costo_total)
