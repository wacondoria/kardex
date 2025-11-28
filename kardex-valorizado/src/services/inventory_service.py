from sqlalchemy import func, and_, case
from sqlalchemy.orm import aliased
from models.database_model import Producto, MovimientoStock, Categoria, Almacen, Empresa
from services.base_service import BaseService
from decimal import Decimal

class InventoryService(BaseService):
    """
    Servicio para gestión de inventarios y valorización.
    """

    def get_valorization_report(self, empresa_id: int, almacen_id: int = None, categoria_id: int = None, solo_stock: bool = True):
        """
        Genera el reporte de valorización optimizado (soluciona N+1 queries).
        
        Args:
            empresa_id: ID de la empresa
            almacen_id: ID del almacén (opcional)
            categoria_id: ID de la categoría (opcional)
            solo_stock: Si es True, filtra productos con stock > 0
            
        Returns:
            List[dict]: Lista de diccionarios con datos de valorización
        """
        # Alias para subconsultas
        ms = aliased(MovimientoStock)
        
        # 1. Subconsulta para obtener el último movimiento por producto (y almacén si aplica)
        # Si se selecciona un almacén específico, agrupamos por producto y ese almacén
        # Si es "Todos los almacenes", necesitamos el último movimiento global por almacén para sumar
        
        if almacen_id:
            # Caso 1: Un almacén específico
            # Subconsulta: Max ID por producto en ese almacén
            subquery = (
                self.session.query(
                    func.max(ms.id).label('max_id')
                )
                .filter(ms.empresa_id == empresa_id)
                .filter(ms.almacen_id == almacen_id)
                .group_by(ms.producto_id)
                .subquery()
            )
        else:
            # Caso 2: Todos los almacenes
            # Subconsulta: Max ID por producto Y almacén (para tener el saldo de cada almacén)
            subquery = (
                self.session.query(
                    func.max(ms.id).label('max_id')
                )
                .filter(ms.empresa_id == empresa_id)
                .group_by(ms.producto_id, ms.almacen_id)
                .subquery()
            )

        # 2. Consulta Principal
        # Unimos Productos con los Movimientos encontrados en la subconsulta
        query = (
            self.session.query(
                Producto.codigo,
                Producto.nombre,
                Categoria.nombre.label('categoria_nombre'),
                Producto.unidad_medida,
                func.sum(MovimientoStock.saldo_cantidad).label('total_cantidad'),
                func.sum(MovimientoStock.saldo_costo_total).label('total_valor'),
                # Si es un solo almacén, el costo unitario es directo. 
                # Si son todos, se calcula promedio ponderado después o en la app.
                # Aquí sumamos costos totales y cantidades.
            )
            .join(Categoria, Producto.categoria_id == Categoria.id)
            .join(MovimientoStock, MovimientoStock.producto_id == Producto.id)
            .join(subquery, MovimientoStock.id == subquery.c.max_id) # Join con el último movimiento
            .filter(Producto.activo == True)
        )

        # Filtros adicionales
        if categoria_id:
            query = query.filter(Producto.categoria_id == categoria_id)
            
        # Agrupamos por producto para sumar saldos de diferentes almacenes (si aplica)
        query = query.group_by(
            Producto.id, 
            Producto.codigo, 
            Producto.nombre, 
            Categoria.nombre, 
            Producto.unidad_medida
        )

        # Filtro de stock (Having porque es sobre agregación sum)
        if solo_stock:
            query = query.having(func.sum(MovimientoStock.saldo_cantidad) > 0)

        # Ordenar
        query = query.order_by(Categoria.nombre, Producto.nombre)

        results = query.all()
        
        # Formatear resultados
        datos = []
        for row in results:
            cantidad = float(row.total_cantidad or 0)
            valor_total = float(row.total_valor or 0)
            
            if cantidad > 0:
                costo_unitario = valor_total / cantidad
            else:
                costo_unitario = 0.0
                
            datos.append({
                'codigo': row.codigo,
                'nombre': row.nombre,
                'categoria': row.categoria_nombre,
                'unidad': row.unidad_medida,
                'cantidad': cantidad,
                'costo_unitario': costo_unitario,
                'valor_total': valor_total,
                'almacen': 'TODOS' if not almacen_id else 'SELECCIONADO' # Simplificado
            })
            
        return datos

    def get_stock_producto(self, producto_id: int, almacen_id: int = None):
        """Obtiene el stock actual de un producto"""
        query = self.session.query(MovimientoStock).filter(
            MovimientoStock.producto_id == producto_id
        )
        
        if almacen_id:
            query = query.filter(MovimientoStock.almacen_id == almacen_id)
            last_mov = query.order_by(MovimientoStock.id.desc()).first()
            return last_mov.saldo_cantidad if last_mov else 0
        else:
            # Suma de últimos movimientos por almacén
            subquery = (
                self.session.query(
                    func.max(MovimientoStock.id).label('max_id')
                )
                .filter(MovimientoStock.producto_id == producto_id)
                .group_by(MovimientoStock.almacen_id)
                .subquery()
            )
            
            total = self.session.query(func.sum(MovimientoStock.saldo_cantidad)).join(
                subquery, MovimientoStock.id == subquery.c.max_id
            ).scalar()
            
            return total or 0

    def recalculate_kardex(self, producto_id: int, empresa_id: int):
        """
        Recalcula todos los saldos y costos promedios de un producto desde cero.
        Crítico para mantener la integridad de datos.
        """
        # 1. Obtener todos los movimientos ordenados cronológicamente
        movimientos = self.session.query(MovimientoStock).filter(
            MovimientoStock.producto_id == producto_id,
            MovimientoStock.empresa_id == empresa_id
        ).order_by(
            MovimientoStock.fecha_documento,
            MovimientoStock.fecha_registro,
            MovimientoStock.id
        ).all()
        
        # Diccionario para mantener estado por almacén
        # saldo_almacen[almacen_id] = {'cantidad': 0.0, 'costo_total': 0.0}
        saldos_almacen = {} 
        
        # Variables globales del producto (para costo promedio ponderado si es global)
        # Asumiremos costo promedio ponderado GLOBAL por empresa (común en Perú)
        # O costo promedio por almacén. El modelo actual parece sugerir saldo por movimiento.
        # Vamos a recalcular basándonos en el flujo cronológico.
        
        saldo_global_cantidad = Decimal('0')
        saldo_global_costo = Decimal('0')
        
        for mov in movimientos:
            # Inicializar saldo almacén si no existe
            if mov.almacen_id not in saldos_almacen:
                saldos_almacen[mov.almacen_id] = Decimal('0')

            cant_entrada = Decimal(str(mov.cantidad_entrada))
            cant_salida = Decimal(str(mov.cantidad_salida))
            costo_unitario_mov = Decimal(str(mov.costo_unitario))
            
            # Lógica de Costo Promedio Ponderado
            # Si es entrada, aumenta saldo y recálcula costo promedio
            if cant_entrada > 0:
                # Nuevo saldo global
                nuevo_saldo_cantidad = saldo_global_cantidad + cant_entrada
                nuevo_saldo_costo = saldo_global_costo + (cant_entrada * costo_unitario_mov)
                
                saldo_global_cantidad = nuevo_saldo_cantidad
                saldo_global_costo = nuevo_saldo_costo
                
                # Actualizar saldo almacén
                saldos_almacen[mov.almacen_id] += cant_entrada
                
            # Si es salida, disminuye saldo y usa costo promedio actual
            elif cant_salida > 0:
                # El costo de salida DEBE ser el costo promedio actual
                # Si no hay saldo, usamos el costo del movimiento (o 0)
                costo_promedio = Decimal('0')
                if saldo_global_cantidad > 0:
                    costo_promedio = saldo_global_costo / saldo_global_cantidad
                
                # Actualizar costo unitario y total de la salida en el registro
                # NOTA: Esto modifica el histórico para corregir costos de salida mal calculados
                mov.costo_unitario = float(costo_promedio)
                mov.costo_total = float(cant_salida * costo_promedio)
                
                # Actualizar saldos globales
                saldo_global_cantidad -= cant_salida
                saldo_global_costo -= (cant_salida * costo_promedio)
                
                # Actualizar saldo almacén
                saldos_almacen[mov.almacen_id] -= cant_salida

            # Actualizar los saldos finales del registro (snapshot)
            # En este modelo, saldo_cantidad parece ser el saldo DEL ALMACÉN después del movimiento
            # O el saldo GLOBAL? Revisando database_model, no es explícito, pero usualmente Kardex es por almacén.
            # Sin embargo, para valoración promedio ponderado, se suele usar el global.
            # Asumiremos que saldo_cantidad en la tabla es el saldo en ESE almacén para control de stock físico.
            
            mov.saldo_cantidad = float(saldos_almacen[mov.almacen_id])
            
            # El saldo_costo_total en la tabla es ambiguo. ¿Es el valor del inventario total o solo de ese almacén?
            # Para consistencia con ValorizacionWindow (que suma saldos), debe ser el valor en ese almacén.
            # Si usamos costo promedio global: Valor Almacen = Cantidad Almacen * Costo Promedio Global
            
            costo_promedio_actual = 0
            if saldo_global_cantidad > 0:
                costo_promedio_actual = saldo_global_costo / saldo_global_cantidad
                
            mov.saldo_costo_total = float(saldos_almacen[mov.almacen_id] * costo_promedio_actual)

        # Commit de todos los cambios
        self.session.commit()
