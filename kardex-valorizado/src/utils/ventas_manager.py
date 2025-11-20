"""
VentasManager - Lógica de negocio para la gestión de ventas.
Archivo: src/utils/ventas_manager.py
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from sqlalchemy.orm import Session
from models.database_model import (
    Venta, VentaDetalle, Producto, Almacen, MovimientoStock,
    TipoMovimiento, TipoDocumento, Moneda, Cliente
)
from utils.kardex_manager import KardexManager
from utils.validation import verificar_estado_anio, AnioCerradoError

class VentasManager:
    def __init__(self, session: Session):
        self.session = session
        self.kardex_manager = KardexManager(session)

    def obtener_stock_actual(self, producto_id, almacen_id, fecha=None):
        """Delegado al KardexManager."""
        return self.kardex_manager.obtener_stock_actual(producto_id, almacen_id, fecha)

    def verificar_stock_suficiente(self, detalles_venta, fecha_doc=None):
        """
        Verifica si hay stock suficiente para todos los detalles de la venta.
        Retorna una lista de errores (strings) si hay insuficiencia, o una lista vacía si todo está bien.
        """
        stock_insuficiente = []
        stock_a_verificar = {} # (prod_id, alm_id) -> cantidad_total

        for det in detalles_venta:
            key = (det['producto_id'], det['almacen_id'])
            stock_a_verificar[key] = stock_a_verificar.get(key, 0) + det['cantidad']

        for (prod_id, alm_id), cantidad_total in stock_a_verificar.items():
            stock_actual = self.obtener_stock_actual(prod_id, alm_id, fecha_doc)
            if cantidad_total > stock_actual:
                stock_insuficiente.append(f"Producto ID {prod_id}: Stock {stock_actual}, Solicitado {cantidad_total}")

        return stock_insuficiente

    def calcular_totales(self, detalles, incluye_igv, moneda, tipo_cambio):
        """
        Calcula subtotal, IGV y total para una lista de detalles.
        """
        DOS_DECIMALES = Decimal('0.01')
        IGV_FACTOR = Decimal('1.18')
        IGV_PORCENTAJE = Decimal('0.18')

        # Primero recalculamos los subtotales de cada detalle para asegurar consistencia
        for det in detalles:
            cantidad = Decimal(str(det['cantidad']))
            precio_unitario = Decimal(str(det['precio_unitario']))
            subtotal_sin_igv = Decimal('0')

            if incluye_igv:
                subtotal_sin_igv = (cantidad * (precio_unitario / IGV_FACTOR)).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            else:
                subtotal_sin_igv = (cantidad * precio_unitario).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

            det['subtotal'] = float(subtotal_sin_igv)

        subtotal_productos = sum(Decimal(str(det['subtotal'])) for det in detalles)

        # Ventas no suele tener costo adicional en este sistema, pero si lo tuviera se sumaría aquí
        subtotal_general_sin_igv = subtotal_productos

        igv = (subtotal_general_sin_igv * IGV_PORCENTAJE).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
        total = (subtotal_general_sin_igv + igv).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

        return subtotal_general_sin_igv, igv, total

    def guardar_venta(self, datos_cabecera, detalles, venta_id=None):
        """
        Crea o actualiza una venta, sus detalles y movimientos de kardex.
        datos_cabecera: dict con las claves correspondientes a los campos de Venta
        detalles: lista de dicts con info de los productos
        venta_id: ID de la venta a editar (None si es nueva)
        """
        fecha_contable = datos_cabecera['fecha_registro_contable']
        verificar_estado_anio(fecha_contable)

        es_edicion = venta_id is not None

        # Validar stock antes de proceder (solo si no es anulación completa,
        # pero aquí asumimos que se quiere guardar una venta válida)
        # Nota: Al editar, si aumentamos cantidad, validamos.
        # Si es nueva, validamos todo.
        # Esta validación debería hacerse ANTES de llamar a este método si se quiere feedback interactivo,
        # pero lo hacemos aquí como red de seguridad.
        if not es_edicion: # En edición es más complejo porque hay que considerar lo que ya estaba reservado
             errores_stock = self.verificar_stock_suficiente(detalles, datos_cabecera['fecha'])
             if errores_stock:
                 raise ValueError("Stock insuficiente:\n" + "\n".join(errores_stock))

        # 1. Cabecera de Venta
        if es_edicion:
            venta = self.session.get(Venta, venta_id)
            if not venta:
                raise ValueError(f"Venta ID {venta_id} no encontrada")

            # Capturar valores originales para anulación de Kardex
            orig_tipo_doc = venta.tipo_documento
            orig_num_doc = venta.numero_documento

            # Actualizar campos
            for key, value in datos_cabecera.items():
                if hasattr(venta, key):
                    setattr(venta, key, value)

            # Cargar detalles originales para comparar
            detalles_originales_obj = self.session.query(VentaDetalle).filter_by(venta_id=venta.id).all()

        else:
            venta = Venta(**datos_cabecera)
            self.session.add(venta)
            self.session.flush() # Para obtener el ID
            detalles_originales_obj = []

        # 2. Procesar Detalles
        ids_detalles_ui = {det.get('detalle_original_id') for det in detalles if det.get('detalle_original_id')}
        ids_detalles_originales = {det.id for det in detalles_originales_obj}

        detalles_a_eliminar_ids = ids_detalles_originales - ids_detalles_ui
        detalles_a_anadir = [det for det in detalles if not det.get('detalle_original_id')]
        detalles_a_modificar = [det for det in detalles if det.get('detalle_original_id') in ids_detalles_originales]

        producto_almacen_afectados = set()
        movimientos_kardex = []

        DOS_DECIMALES = Decimal('0.01')
        IGV_FACTOR = Decimal('1.18')

        # A. Eliminar detalles
        if es_edicion and detalles_a_eliminar_ids:
            for detalle_id in detalles_a_eliminar_ids:
                detalle_obj = self.session.get(VentaDetalle, detalle_id)
                if detalle_obj:
                    producto_almacen_afectados.add((detalle_obj.producto_id, detalle_obj.almacen_id))

                    # Movimiento de anulación (Devolución)
                    # Usamos los valores originales del documento por si cambiaron en la edición
                    mov_original = self.session.query(MovimientoStock).filter_by(
                        tipo=TipoMovimiento.VENTA,
                        tipo_documento=orig_tipo_doc,
                        numero_documento=orig_num_doc,
                        producto_id=detalle_obj.producto_id, almacen_id=detalle_obj.almacen_id,
                    ).order_by(MovimientoStock.id.desc()).first()

                    if mov_original:
                        ajuste_entrada = MovimientoStock(
                            empresa_id=mov_original.empresa_id, producto_id=mov_original.producto_id, almacen_id=mov_original.almacen_id,
                            tipo=TipoMovimiento.DEVOLUCION_VENTA,
                            tipo_documento=venta.tipo_documento, numero_documento=venta.numero_documento,
                            fecha_documento=venta.fecha, cliente_id=venta.cliente_id,
                            cantidad_entrada=mov_original.cantidad_salida, cantidad_salida=0,
                            costo_unitario=mov_original.costo_unitario, costo_total=mov_original.costo_total,
                            saldo_cantidad=0, saldo_costo_total=0, moneda=venta.moneda, tipo_cambio=float(venta.tipo_cambio),
                            observaciones=f"Ajuste por edición de venta ID {venta.id} (Detalle ID {detalle_id} eliminado)"
                        )
                        movimientos_kardex.append(ajuste_entrada)

                    self.session.delete(detalle_obj)

        # B. Añadir nuevos detalles
        for det_ui in detalles_a_anadir:
            cantidad_dec = Decimal(str(det_ui['cantidad']))
            precio_unitario_ui = Decimal(str(det_ui['precio_unitario']))

            if venta.incluye_igv:
                precio_sin_igv = (precio_unitario_ui / IGV_FACTOR).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            else:
                precio_sin_igv = precio_unitario_ui
            subtotal_det_sin_igv = (cantidad_dec * precio_sin_igv).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

            # Obtener costo del Kardex
            costo_unitario_kardex = self.kardex_manager.obtener_costo_promedio_actual(
                det_ui['producto_id'], det_ui['almacen_id'], venta.fecha
            )
            costo_total_kardex = (cantidad_dec * Decimal(str(costo_unitario_kardex))).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

            nuevo_detalle = VentaDetalle(
                venta_id=venta.id,
                producto_id=det_ui['producto_id'],
                almacen_id=det_ui['almacen_id'],
                cantidad=cantidad_dec,
                precio_unitario_sin_igv=precio_sin_igv,
                subtotal=subtotal_det_sin_igv,
                costo_unitario_kardex=costo_unitario_kardex,
                costo_total_kardex=costo_total_kardex
            )
            self.session.add(nuevo_detalle)
            producto_almacen_afectados.add((det_ui['producto_id'], det_ui['almacen_id']))

            almacen = self.session.get(Almacen, det_ui['almacen_id'])
            if almacen:
                nuevo_movimiento = MovimientoStock(
                    empresa_id=almacen.empresa_id, producto_id=det_ui['producto_id'], almacen_id=det_ui['almacen_id'],
                    tipo=TipoMovimiento.VENTA,
                    tipo_documento=venta.tipo_documento, numero_documento=venta.numero_documento,
                    fecha_documento=venta.fecha, cliente_id=venta.cliente_id,
                    cantidad_entrada=0, cantidad_salida=cantidad_dec,
                    costo_unitario=float(costo_unitario_kardex),
                    costo_total=float(costo_total_kardex),
                    saldo_cantidad=0, saldo_costo_total=0,
                    moneda=venta.moneda, tipo_cambio=float(venta.tipo_cambio),
                    observaciones=f"Registro por {'edición (añadido)' if es_edicion else 'nueva venta'} ID {venta.id}"
                )
                movimientos_kardex.append(nuevo_movimiento)

        # C. Modificar detalles existentes
        if es_edicion:
            for det_ui in detalles_a_modificar:
                detalle_obj = self.session.get(VentaDetalle, det_ui['detalle_original_id'])
                if not detalle_obj: continue

                producto_id_original = detalle_obj.producto_id
                almacen_id_original = detalle_obj.almacen_id
                producto_almacen_afectados.add((producto_id_original, almacen_id_original))

                cantidad_dec = Decimal(str(det_ui['cantidad']))
                precio_unitario_ui = Decimal(str(det_ui['precio_unitario']))

                if venta.incluye_igv:
                    precio_sin_igv = (precio_unitario_ui / IGV_FACTOR).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                else:
                    precio_sin_igv = precio_unitario_ui
                subtotal_det_sin_igv = (cantidad_dec * precio_sin_igv).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

                costo_unitario_final = self.kardex_manager.obtener_costo_promedio_actual(
                    det_ui['producto_id'], det_ui['almacen_id'], venta.fecha
                )
                subtotal_final_det_kardex = (cantidad_dec * Decimal(str(costo_unitario_final))).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

                detalle_obj.producto_id = det_ui['producto_id']
                detalle_obj.almacen_id = det_ui['almacen_id']
                detalle_obj.cantidad = cantidad_dec
                detalle_obj.precio_unitario_sin_igv = precio_sin_igv
                detalle_obj.subtotal = subtotal_det_sin_igv
                detalle_obj.costo_unitario_kardex = costo_unitario_final
                detalle_obj.costo_total_kardex = subtotal_final_det_kardex

                producto_almacen_afectados.add((detalle_obj.producto_id, detalle_obj.almacen_id))

                # 1. Anular movimiento original
                # Usamos los valores originales del documento por si cambiaron en la edición
                mov_original = self.session.query(MovimientoStock).filter_by(
                    tipo=TipoMovimiento.VENTA,
                    tipo_documento=orig_tipo_doc,
                    numero_documento=orig_num_doc,
                    producto_id=producto_id_original, almacen_id=almacen_id_original
                ).order_by(MovimientoStock.id.desc()).first()

                if mov_original:
                    ajuste_entrada = MovimientoStock(
                        empresa_id=mov_original.empresa_id, producto_id=producto_id_original, almacen_id=almacen_id_original,
                        tipo=TipoMovimiento.DEVOLUCION_VENTA,
                        tipo_documento=venta.tipo_documento, numero_documento=venta.numero_documento,
                        fecha_documento=venta.fecha, cliente_id=venta.cliente_id,
                        cantidad_entrada=mov_original.cantidad_salida, cantidad_salida=0,
                        costo_unitario=mov_original.costo_unitario, costo_total=mov_original.costo_total,
                        saldo_cantidad=0, saldo_costo_total=0, moneda=venta.moneda, tipo_cambio=float(venta.tipo_cambio),
                        observaciones=f"Ajuste (anulación) por edición Venta ID {venta.id} (Detalle ID {detalle_obj.id})"
                    )
                    movimientos_kardex.append(ajuste_entrada)

                # 2. Crear nuevo movimiento
                almacen_nuevo = self.session.get(Almacen, detalle_obj.almacen_id)
                if almacen_nuevo:
                    ajuste_salida = MovimientoStock(
                        empresa_id=almacen_nuevo.empresa_id, producto_id=detalle_obj.producto_id, almacen_id=detalle_obj.almacen_id,
                        tipo=TipoMovimiento.VENTA,
                        tipo_documento=venta.tipo_documento, numero_documento=venta.numero_documento,
                        fecha_documento=venta.fecha, cliente_id=venta.cliente_id,
                        cantidad_entrada=0, cantidad_salida=cantidad_dec,
                        costo_unitario=float(costo_unitario_final), costo_total=float(subtotal_final_det_kardex),
                        saldo_cantidad=0, saldo_costo_total=0, moneda=venta.moneda, tipo_cambio=float(venta.tipo_cambio),
                        observaciones=f"Ajuste (nuevo) por edición Venta ID {venta.id} (Detalle ID {detalle_obj.id})"
                    )
                    movimientos_kardex.append(ajuste_salida)

        # 3. Persistir movimientos y recalcular kardex
        for mov in movimientos_kardex:
            self.session.add(mov)

        if producto_almacen_afectados:
            self.session.flush()
            self.kardex_manager.recalcular_kardex_posterior(producto_almacen_afectados, venta.fecha)

        self.session.commit()
        return venta

    def eliminar_venta(self, venta_id):
        """
        Elimina una venta y revierte sus movimientos de kardex.
        """
        venta = self.session.get(Venta, venta_id)
        if not venta:
            raise ValueError("Venta no encontrada")

        verificar_estado_anio(venta.fecha_registro_contable or venta.fecha)

        producto_almacen_afectados = set()
        fecha_venta = venta.fecha
        tipo_doc = venta.tipo_documento
        num_doc = venta.numero_documento

        detalles = self.session.query(VentaDetalle).filter_by(venta_id=venta.id).all()
        for det in detalles:
            producto_almacen_afectados.add((det.producto_id, det.almacen_id))

            mov_original = self.session.query(MovimientoStock).filter_by(
                tipo=TipoMovimiento.VENTA,
                tipo_documento=tipo_doc,
                numero_documento=num_doc,
                producto_id=det.producto_id,
                almacen_id=det.almacen_id
            ).first()

            if mov_original:
                self.session.delete(mov_original)

            self.session.delete(det)

        self.session.delete(venta)
        self.session.flush()

        if producto_almacen_afectados:
            self.kardex_manager.recalcular_kardex_posterior(producto_almacen_afectados, fecha_venta)

        self.session.commit()
