"""
Gestión de Requisiciones - Sistema Kardex Valorizado
Archivo: src/views/requisiciones_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox,
                              QTextEdit, QMessageBox, QDialog, QFormLayout, 
                              QHeaderView, QGroupBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from sqlalchemy import extract, func
from sqlalchemy.orm import joinedload

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, Requisicion, RequisicionDetalle,
                                   Producto, Almacen, Empresa, Destino,
                                   MovimientoStock, TipoMovimiento, MetodoValuacion)
from utils.widgets import UpperLineEdit, SearchableComboBox
from utils.app_context import app_context
from utils.button_utils import style_button
from utils.kardex_manager import KardexManager


class RequisicionDialog(QDialog):
    """Diálogo para crear y editar requisiciones"""
    
    def __init__(self, parent=None, user_info=None, requisicion_a_editar=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.user_info = user_info
        self.requisicion_original = requisicion_a_editar
        self.detalles_requisicion = [] # Lista de diccionarios para la UI
        self.detalles_originales_obj = [] # Lista de objetos SQLAlchemy originales
        self.selected_year = app_context.get_selected_year()
        self.kardex_manager = KardexManager(self.session)

        self.init_ui()
        self.cargar_datos_iniciales()

        if self.requisicion_original:
            self.cargar_datos_para_edicion()

    def init_ui(self):
        self.setWindowTitle("Nueva Requisición" if not self.requisicion_original else "Editar Requisición")
        self.setMinimumSize(1000, 650)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        titulo = QLabel("📤 Nueva Requisición de Salida")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)
        
        # === DATOS DE LA REQUISICIÓN ===
        grupo_req = QGroupBox("Datos de la Requisición")
        form_req = QFormLayout()
        form_req.setSpacing(10)
        
        # Fila 1: Fecha, Número, Destino
        fila1 = QHBoxLayout()
        
        self.date_fecha = QDateEdit()
        self.date_fecha.setCalendarPopup(True)
        today = QDate.currentDate()
        if today.year() == self.selected_year:
            self.date_fecha.setDate(today)
        else:
            self.date_fecha.setDate(QDate(self.selected_year, 1, 1))
        self.date_fecha.setDisplayFormat("dd/MM/yyyy")
        
        self.txt_numero = UpperLineEdit()
        self.txt_numero.setPlaceholderText("Se generará automáticamente")
        self.txt_numero.setReadOnly(True)
        self.txt_numero.setStyleSheet("background-color: #f0f0f0;")
        
        fila1.addWidget(QLabel("Fecha:"))
        fila1.addWidget(self.date_fecha)
        fila1.addWidget(QLabel("Número:"))
        fila1.addWidget(self.txt_numero)
        fila1.addStretch()
        
        form_req.addRow("", fila1)
        
        # Destino
        destino_layout = QHBoxLayout()
        self.cmb_destino = SearchableComboBox()
        self.cmb_destino.setMinimumWidth(300)
        
        btn_nuevo_destino = QPushButton()
        style_button(btn_nuevo_destino, 'add', "Nuevo")
        btn_nuevo_destino.clicked.connect(self.nuevo_destino)
        
        destino_layout.addWidget(self.cmb_destino)
        destino_layout.addWidget(btn_nuevo_destino)
        destino_layout.addStretch()
        
        form_req.addRow("Destino:*", destino_layout)
        
        # Solicitante
        self.txt_solicitante = UpperLineEdit()
        self.txt_solicitante.setPlaceholderText("Nombre de quien solicita")
        form_req.addRow("Solicitante:", self.txt_solicitante)
        
        grupo_req.setLayout(form_req)
        layout.addWidget(grupo_req)
        
        # === PRODUCTOS ===
        grupo_productos = QGroupBox("Productos")
        productos_layout = QVBoxLayout()
        
        # Selector de producto
        selector_layout = QHBoxLayout()
        
        self.cmb_producto = SearchableComboBox()
        self.cmb_producto.setMinimumWidth(300)
        self.cmb_producto.currentIndexChanged.connect(self.producto_seleccionado)
        
        self.cmb_almacen = SearchableComboBox()
        self.cmb_almacen.currentIndexChanged.connect(self.almacen_seleccionado)
        
        self.lbl_stock_disponible = QLabel("Stock: -")
        self.lbl_stock_disponible.setStyleSheet("font-weight: bold; color: #1a73e8;")

        self.lbl_costo_stock_disponible = QLabel("Costo Stock: S/ -")
        self.lbl_costo_stock_disponible.setStyleSheet("font-weight: bold; color: #1a73e8;")
        
        self.spn_cantidad = QDoubleSpinBox()
        self.spn_cantidad.setRange(0.01, 999999)
        self.spn_cantidad.setDecimals(2)
        self.spn_cantidad.setValue(1.00)
        
        btn_agregar = QPushButton()
        style_button(btn_agregar, 'add', "Agregar")
        btn_agregar.clicked.connect(self.agregar_producto)
        
        selector_layout.addWidget(QLabel("Producto:"))
        selector_layout.addWidget(self.cmb_producto, 2)
        selector_layout.addWidget(QLabel("Almacén:"))
        selector_layout.addWidget(self.cmb_almacen, 1)
        selector_layout.addWidget(self.lbl_stock_disponible)
        selector_layout.addWidget(self.lbl_costo_stock_disponible)
        selector_layout.addWidget(QLabel("Cantidad:"))
        selector_layout.addWidget(self.spn_cantidad)
        selector_layout.addWidget(btn_agregar)
        
        productos_layout.addLayout(selector_layout)
        
        # Tabla de productos
        self.tabla_productos = QTableWidget()
        self.tabla_productos.setColumnCount(7)
        self.tabla_productos.setHorizontalHeaderLabels([
            "Producto", "Almacén", "Stock Disp.", "Cantidad", "Costo Unit.", "Costo Total", "Acción"
        ])
        self.tabla_productos.setMaximumHeight(200)
        
        header = self.tabla_productos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tabla_productos.setColumnWidth(6, 80)
        
        productos_layout.addWidget(self.tabla_productos)
        
        grupo_productos.setLayout(productos_layout)
        layout.addWidget(grupo_productos)
        
        # Observaciones
        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setMaximumHeight(60)
        self.txt_observaciones.setPlaceholderText("Observaciones adicionales...")
        layout.addWidget(QLabel("Observaciones:"))
        layout.addWidget(self.txt_observaciones)
        
        # Resumen
        self.lbl_resumen = QLabel("Total productos: 0 | Costo Total: S/ 0.00")
        self.lbl_resumen.setStyleSheet("""
            background-color: #e8f0fe;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
            color: #1a73e8;
        """)
        layout.addWidget(self.lbl_resumen)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f4;
                padding: 10px 30px;
                border-radius: 5px;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)
        
        self.btn_guardar = QPushButton("Guardar Requisición")
        style_button(self.btn_guardar, 'add', "Guardar Requisición")
        self.btn_guardar.clicked.connect(self.guardar_requisicion)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def cargar_datos_para_edicion(self):
        """Rellena los campos del diálogo con los datos de la requisición a editar."""
        if not self.requisicion_original:
            return

        self.setWindowTitle(f"✏️ Editando Requisición: {self.requisicion_original.numero_requisicion}")
        self.btn_guardar.setText("Guardar Cambios")

        # Bloquear campos clave
        self.date_fecha.setDate(QDate.fromString(self.requisicion_original.fecha.strftime('%Y-%m-%d'), 'yyyy-MM-dd'))
        self.date_fecha.setEnabled(False)
        self.txt_numero.setText(self.requisicion_original.numero_requisicion)

        # Cargar datos
        index_destino = self.cmb_destino.findData(self.requisicion_original.destino_id)
        if index_destino != -1:
            self.cmb_destino.setCurrentIndex(index_destino)

        self.txt_solicitante.setText(self.requisicion_original.solicitante or "")
        self.txt_observaciones.setPlainText(self.requisicion_original.observaciones or "")

        # Cargar detalles
        self.detalles_originales_obj = self.session.query(RequisicionDetalle).filter_by(requisicion_id=self.requisicion_original.id).all()
        for det_obj in self.detalles_originales_obj:
            producto = self.session.query(Producto).get(det_obj.producto_id)
            almacen = self.session.query(Almacen).get(det_obj.almacen_id)
            empresa = self.session.query(Empresa).get(almacen.empresa_id)

            # Para la edición, calculamos el costo basado en la cantidad original
            costo_unitario, costo_total = self.kardex_manager.calcular_costo_salida(
                empresa.id, det_obj.producto_id, det_obj.almacen_id, float(det_obj.cantidad)
            )

            detalle_dict = {
                'producto_id': det_obj.producto_id,
                'producto_nombre': f"{producto.codigo} - {producto.nombre}",
                'almacen_id': det_obj.almacen_id,
                'almacen_nombre': almacen.nombre,
                'stock_disponible': 0, # No es crítico para la edición
                'cantidad': float(det_obj.cantidad),
                'costo_unitario': costo_unitario,
                'costo_total': costo_total,
                'detalle_original_id': det_obj.id
            }
            self.detalles_requisicion.append(detalle_dict)

        self.actualizar_tabla_productos()

    def keyPressEvent(self, event):
        """Captura la pulsación de teclas en el diálogo."""
        if event.key() == Qt.Key.Key_F4:
            self.guardar_requisicion()
        else:
            super().keyPressEvent(event)
    
    def cargar_datos_iniciales(self):
        """Carga destinos, productos y almacenes"""
        # Destinos
        destinos = self.session.query(Destino).filter_by(activo=True).order_by(Destino.nombre).all()
        
        if not destinos:
            # Crear algunos destinos por defecto
            destinos_default = [
                Destino(nombre="Producción", descripcion="Área de producción"),
                Destino(nombre="Ventas", descripcion="Salida por ventas"),
                Destino(nombre="Mantenimiento", descripcion="Área de mantenimiento")
            ]
            for dest in destinos_default:
                self.session.add(dest)
            self.session.commit()
            destinos = destinos_default
        
        for dest in destinos:
            self.cmb_destino.addItem(dest.nombre, dest.id)
        
        # Productos: Cargar solo productos con stock > 0
        # 1. Statement para obtener el ID del último movimiento para cada producto/almacén.
        #    No se usa .subquery() para evitar un SAWarning. La Query se pasa directamente a IN().
        subquery_ultimo_mov_id_stmt = self.session.query(
            func.max(MovimientoStock.id)
        ).group_by(
            MovimientoStock.producto_id,
            MovimientoStock.almacen_id
        )

        # 2. Subconsulta para obtener el saldo total de cada producto sumando los saldos de cada almacén
        subquery_stock_total = self.session.query(
            MovimientoStock.producto_id,
            func.sum(MovimientoStock.saldo_cantidad).label('stock_total')
        ).filter(
            MovimientoStock.id.in_(subquery_ultimo_mov_id_stmt)
        ).group_by(
            MovimientoStock.producto_id
        ).subquery()

        # 3. Consulta principal para obtener productos activos con stock total > 0
        productos_con_stock = self.session.query(
            Producto
        ).join(
            subquery_stock_total, Producto.id == subquery_stock_total.c.producto_id
        ).filter(
            subquery_stock_total.c.stock_total > 0,
            Producto.activo == True
        ).order_by(Producto.nombre).all()

        for prod in productos_con_stock:
            self.cmb_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)
        
        # Almacenes
        self.cargar_almacenes()
        
        # Generar número
        self.generar_numero()
    
    def cargar_almacenes(self):
        """Carga almacenes y selecciona el principal por defecto si es aplicable."""
        self.cmb_almacen.clear()
        
        todos_los_almacenes = self.session.query(Almacen).join(Empresa).filter(
            Almacen.activo == True,
            Empresa.activo == True
        ).all()

        if not todos_los_almacenes:
            return

        almacen_principal = None
        for alm in todos_los_almacenes:
            self.cmb_almacen.addItem(
                f"{alm.empresa.razon_social} - {alm.nombre}",
                alm.id
            )
            if alm.es_principal:
                almacen_principal = alm

        if len(todos_los_almacenes) == 1:
            self.cmb_almacen.setCurrentIndex(0)
        elif almacen_principal:
            index = self.cmb_almacen.findData(almacen_principal.id)
            if index != -1:
                self.cmb_almacen.setCurrentIndex(index)
        else:
            self.cmb_almacen.setCurrentIndex(-1)
    
    def producto_seleccionado(self):
        """Cuando cambia el producto"""
        self.actualizar_stock_disponible()
    
    def almacen_seleccionado(self):
        """Cuando cambia el almacén"""
        self.actualizar_stock_disponible()
    
    def actualizar_stock_disponible(self):
        """Muestra el stock disponible del producto en el almacén"""
        prod_id = self.cmb_producto.currentData()
        alm_id = self.cmb_almacen.currentData()
        
        if not prod_id or not alm_id:
            self.lbl_stock_disponible.setText("Stock: -")
            self.lbl_costo_stock_disponible.setText("Costo Stock: S/ -")
            return
        
        almacen = self.session.query(Almacen).get(alm_id)
        
        # Obtener último movimiento
        ultimo_mov = self.session.query(MovimientoStock).filter_by(
            empresa_id=almacen.empresa_id,
            producto_id=prod_id,
            almacen_id=alm_id
        ).order_by(MovimientoStock.id.desc()).first()
        
        if ultimo_mov:
            stock = ultimo_mov.saldo_cantidad
            costo_stock = ultimo_mov.saldo_costo_total
            color = "#34a853" if stock > 0 else "#ea4335"
            self.lbl_stock_disponible.setText(f"Stock: {stock:.2f}")
            self.lbl_costo_stock_disponible.setText(f"Costo Stock: S/ {costo_stock:.2f}")
            self.lbl_stock_disponible.setStyleSheet(f"font-weight: bold; color: {color};")
            self.lbl_costo_stock_disponible.setStyleSheet(f"font-weight: bold; color: {color};")
        else:
            self.lbl_stock_disponible.setText("Stock: 0.00")
            self.lbl_costo_stock_disponible.setText("Costo Stock: S/ 0.00")
            self.lbl_stock_disponible.setStyleSheet("font-weight: bold; color: #ea4335;")
            self.lbl_costo_stock_disponible.setStyleSheet("font-weight: bold; color: #ea4335;")
    
    def generar_numero(self):
        """Genera el número correlativo de requisición, reseteando por año."""
        # Find the last requisition *within the selected year*
        ultima_del_anio = self.session.query(Requisicion).filter(
            extract('year', Requisicion.fecha) == self.selected_year
        ).order_by(Requisicion.id.desc()).first()
        
        numero = 1
        if ultima_del_anio:
            try:
                # Tries to parse 'REQ-NNNNNN' format
                numero = int(ultima_del_anio.numero_requisicion.split('-')[1]) + 1
            except (ValueError, IndexError):
                # If parsing fails for any reason, fall back to counting for safety
                numero = self.session.query(Requisicion).filter(extract('year', Requisicion.fecha) == self.selected_year).count() + 1
        
        self.txt_numero.setText(f"REQ-{numero:06d}")
    
    def nuevo_destino(self):
        """Abre diálogo para crear nuevo destino"""
        nombre, ok = QLineEdit().text(), True
        from PyQt6.QtWidgets import QInputDialog
        
        nombre, ok = QInputDialog.getText(
            self,
            "Nuevo Destino",
            "Nombre del destino:"
        )
        
        if ok and nombre:
            destino = Destino(nombre=nombre.strip())
            self.session.add(destino)
            self.session.commit()
            
            self.cmb_destino.addItem(destino.nombre, destino.id)
            self.cmb_destino.setCurrentIndex(self.cmb_destino.count() - 1)
    
    def agregar_producto(self):
        """Agrega un producto a la lista"""
        prod_id = self.cmb_producto.currentData()
        alm_id = self.cmb_almacen.currentData()
        cantidad = self.spn_cantidad.value()
        
        if not prod_id or not alm_id:
            QMessageBox.warning(self, "Error", "Seleccione producto y almacén")
            return
        
        if cantidad <= 0:
            QMessageBox.warning(self, "Error", "La cantidad debe ser mayor a cero")
            return
        
        # Verificar si el producto ya está en la lista
        for detalle_existente in self.detalles_requisicion:
            if detalle_existente['producto_id'] == prod_id:
                QMessageBox.warning(self, "Producto Duplicado",
                                    "Este producto ya ha sido añadido a la requisición.")
                return

        # Verificar stock
        almacen = self.session.query(Almacen).get(alm_id)
        ultimo_mov = self.session.query(MovimientoStock).filter_by(
            empresa_id=almacen.empresa_id,
            producto_id=prod_id,
            almacen_id=alm_id
        ).order_by(MovimientoStock.id.desc()).first()
        
        stock_disponible = ultimo_mov.saldo_cantidad if ultimo_mov else 0
        
        if cantidad > stock_disponible:
            QMessageBox.warning(
                self,
                "Stock Insuficiente",
                f"Stock disponible: {stock_disponible:.2f}\nCantidad solicitada: {cantidad:.2f}\n\n"
                "No hay suficiente stock para esta salida."
            )
            return
        
        producto = self.session.query(Producto).get(prod_id)
        
        empresa = self.session.query(Empresa).get(almacen.empresa_id)
        costo_unitario, costo_total = self.kardex_manager.calcular_costo_salida(
            empresa.id, prod_id, alm_id, cantidad
        )

        # Agregar a lista
        detalle = {
            'producto_id': prod_id,
            'producto_nombre': f"{producto.codigo} - {producto.nombre}",
            'almacen_id': alm_id,
            'almacen_nombre': almacen.nombre,
            'stock_disponible': stock_disponible,
            'cantidad': cantidad,
            'costo_unitario': costo_unitario,
            'costo_total': costo_total
        }
        
        self.detalles_requisicion.append(detalle)
        self.actualizar_tabla_productos()
        
        # Limpiar
        self.spn_cantidad.setValue(1.00)
    
    def actualizar_tabla_productos(self):
        """Actualiza la tabla de productos"""
        self.tabla_productos.setRowCount(len(self.detalles_requisicion))
        
        costo_total_requisicion = 0
        for row, det in enumerate(self.detalles_requisicion):
            self.tabla_productos.setItem(row, 0, QTableWidgetItem(det['producto_nombre']))
            self.tabla_productos.setItem(row, 1, QTableWidgetItem(det['almacen_nombre']))
            self.tabla_productos.setItem(row, 2, QTableWidgetItem(f"{det['stock_disponible']:.2f}"))
            self.tabla_productos.setItem(row, 3, QTableWidgetItem(f"{det['cantidad']:.2f}"))
            self.tabla_productos.setItem(row, 4, QTableWidgetItem(f"S/ {det['costo_unitario']:.2f}"))
            self.tabla_productos.setItem(row, 5, QTableWidgetItem(f"S/ {det['costo_total']:.2f}"))
            costo_total_requisicion += det['costo_total']
            
            # Botón eliminar
            btn_eliminar = QPushButton("✕")
            btn_eliminar.setStyleSheet("background-color: #ea4335; color: white; border-radius: 3px;")
            btn_eliminar.clicked.connect(lambda checked, r=row: self.eliminar_producto(r))
            self.tabla_productos.setCellWidget(row, 6, btn_eliminar)
        
        # Actualizar resumen
        self.lbl_resumen.setText(f"Total productos: {len(self.detalles_requisicion)} | Costo Total: S/ {costo_total_requisicion:.2f}")
    
    def eliminar_producto(self, row):
        """Elimina un producto de la lista"""
        if 0 <= row < len(self.detalles_requisicion):
            del self.detalles_requisicion[row]
            self.actualizar_tabla_productos()
    
    def guardar_requisicion(self):
        """Guarda una requisición nueva o actualiza una existente."""
        if not self.cmb_destino.currentData():
            QMessageBox.warning(self, "Error", "Seleccione un destino")
            return
        
        if not self.detalles_requisicion:
            QMessageBox.warning(self, "Error", "Agregue al menos un producto")
            return

        es_edicion = self.requisicion_original is not None

        try:
            if es_edicion:
                requisicion = self.session.get(Requisicion, self.requisicion_original.id)
                requisicion.destino_id = self.cmb_destino.currentData()
                requisicion.solicitante = self.txt_solicitante.text().strip() or None
                requisicion.observaciones = self.txt_observaciones.toPlainText().strip() or None
            else:
                requisicion = Requisicion(
                    destino_id=self.cmb_destino.currentData(),
                    numero_requisicion=self.txt_numero.text(),
                    fecha=self.date_fecha.date().toPyDate(),
                    solicitante=self.txt_solicitante.text().strip() or None,
                    observaciones=self.txt_observaciones.toPlainText().strip() or None
                )
                self.session.add(requisicion)
                self.session.flush()

            # Lógica para manejar detalles (eliminar, añadir, modificar)
            ids_detalles_ui = {det.get('detalle_original_id') for det in self.detalles_requisicion if det.get('detalle_original_id')}
            ids_detalles_originales = {det.id for det in self.detalles_originales_obj}
            
            detalles_a_eliminar_ids = ids_detalles_originales - ids_detalles_ui
            detalles_a_anadir_ui = [det for det in self.detalles_requisicion if not det.get('detalle_original_id')]
            detalles_a_modificar_ui = [det for det in self.detalles_requisicion if det.get('detalle_original_id') in ids_detalles_originales]

            # 1. Eliminar detalles y revertir movimientos
            for detalle_id in detalles_a_eliminar_ids:
                detalle_obj = self.session.get(RequisicionDetalle, detalle_id)
                if detalle_obj:
                    almacen = self.session.get(Almacen, detalle_obj.almacen_id)
                    costo_unitario, costo_total = self.kardex_manager.calcular_costo_salida(
                        self.session.get(Empresa, almacen.empresa_id),
                        detalle_obj.producto_id,
                        detalle_obj.almacen_id,
                        float(detalle_obj.cantidad)
                    )
                    self.kardex_manager.registrar_movimiento(
                        empresa_id=almacen.empresa_id,
                        producto_id=detalle_obj.producto_id,
                        almacen_id=detalle_obj.almacen_id,
                        tipo=TipoMovimiento.DEVOLUCION_REQUISICION,
                        cantidad_entrada=detalle_obj.cantidad,
                        cantidad_salida=0,
                        costo_unitario=costo_unitario,
                        costo_total=costo_total,
                        numero_documento=requisicion.numero_requisicion,
                        fecha_documento=requisicion.fecha,
                        observaciones=f"Reversión por edición de Requisición ID {requisicion.id}"
                    )
                    self.session.delete(detalle_obj)

            # 2. Añadir nuevos detalles
            for det_ui in detalles_a_anadir_ui:
                self.crear_detalle_y_movimiento(requisicion, det_ui, "Nueva línea en edición")

            # 3. Modificar detalles existentes
            for det_ui in detalles_a_modificar_ui:
                detalle_obj = self.session.get(RequisicionDetalle, det_ui['detalle_original_id'])
                cantidad_original = Decimal(str(detalle_obj.cantidad))
                cantidad_nueva = Decimal(str(det_ui['cantidad']))
                diferencia = cantidad_nueva - cantidad_original

                if diferencia != 0:
                    almacen = self.session.get(Almacen, detalle_obj.almacen_id)
                    costo_unitario, costo_total_dif = self.kardex_manager.calcular_costo_salida(
                        almacen.empresa_id,
                        detalle_obj.producto_id,
                        detalle_obj.almacen_id,
                        float(abs(diferencia))
                    )
                    self.kardex_manager.registrar_movimiento(
                        empresa_id=almacen.empresa_id,
                        producto_id=detalle_obj.producto_id,
                        almacen_id=detalle_obj.almacen_id,
                        tipo=TipoMovimiento.AJUSTE_NEGATIVO if diferencia > 0 else TipoMovimiento.AJUSTE_POSITIVO,
                        cantidad_entrada=abs(diferencia) if diferencia < 0 else 0,
                        cantidad_salida=abs(diferencia) if diferencia > 0 else 0,
                        costo_unitario=costo_unitario,
                        costo_total=costo_total_dif,
                        numero_documento=requisicion.numero_requisicion,
                        fecha_documento=requisicion.fecha,
                        observaciones=f"Ajuste por edición de Req. ID {requisicion.id}"
                    )

                detalle_obj.cantidad = cantidad_nueva
                detalle_obj.producto_id = det_ui['producto_id']
                detalle_obj.almacen_id = det_ui['almacen_id']

            if not es_edicion:
                for det in self.detalles_requisicion:
                    self.crear_detalle_y_movimiento(requisicion, det, f"Requisición {requisicion.numero_requisicion}")

            self.session.commit()
            QMessageBox.information(self, "Éxito", f"Requisición {'actualizada' if es_edicion else 'registrada'} exitosamente.")
            self.accept()

        except Exception as e:
            self.session.rollback()
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al guardar requisición:\n{str(e)}")

    def crear_detalle_y_movimiento(self, requisicion, det_dict, observacion):
        """Crea un RequisicionDetalle y su MovimientoStock asociado."""
        detalle = RequisicionDetalle(
            requisicion_id=requisicion.id,
            producto_id=det_dict['producto_id'],
            almacen_id=det_dict['almacen_id'],
            cantidad=det_dict['cantidad']
        )
        self.session.add(detalle)

        almacen = self.session.query(Almacen).get(det_dict['almacen_id'])
        empresa = self.session.query(Empresa).get(almacen.empresa_id)
        costo_unitario, costo_total = self.kardex_manager.calcular_costo_salida(
            empresa.id, det_dict['producto_id'], det_dict['almacen_id'], det_dict['cantidad']
        )

        self.kardex_manager.registrar_movimiento(
            empresa_id=almacen.empresa_id,
            producto_id=det_dict['producto_id'],
            almacen_id=det_dict['almacen_id'],
            tipo=TipoMovimiento.REQUISICION,
            cantidad_entrada=0,
            cantidad_salida=det_dict['cantidad'],
            costo_unitario=costo_unitario,
            costo_total=costo_total,
            numero_documento=requisicion.numero_requisicion,
            fecha_documento=requisicion.fecha,
            destino_id=requisicion.destino_id,
            observaciones=observacion
        )

class RequisicionesWindow(QWidget):
    """Ventana principal de requisiciones"""
    
    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.requisiciones_mostradas = []
        self.kardex_manager = KardexManager(self.session)
        self.init_ui()
        self.cargar_requisiciones()

    def keyPressEvent(self, event):
        """Captura la pulsación de F2 para crear y F6 para editar."""
        if event.key() == Qt.Key.Key_F2:
            self.nueva_requisicion()
        elif event.key() == Qt.Key.Key_F6:
            fila = self.tabla.currentRow()
            if fila != -1 and fila < len(self.requisiciones_mostradas):
                requisicion_seleccionada = self.requisiciones_mostradas[fila]
                self.editar_requisicion(requisicion_seleccionada)
        else:
            super().keyPressEvent(event)
    
    def init_ui(self):
        self.setWindowTitle("Gestión de Requisiciones")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("📤 Gestión de Requisiciones")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        btn_nueva = QPushButton()
        style_button(btn_nueva, 'add', "Nueva Requisición")
        btn_nueva.clicked.connect(self.nueva_requisicion)
        
        if self.user_info and self.user_info.get('licencia_vencida'):
            btn_nueva.setEnabled(False)
            btn_nueva.setToolTip("Licencia vencida - Solo consulta")
        
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nueva)
        
        # Filtros
        filtro_layout = QHBoxLayout()
        
        selected_year = app_context.get_selected_year()

        lbl_desde = QLabel("Desde:")
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDate(QDate(selected_year, 1, 1))
        self.date_desde.setDisplayFormat("dd/MM/yyyy")
        self.date_desde.dateChanged.connect(self.cargar_requisiciones)
        
        lbl_hasta = QLabel("Hasta:")
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDate(QDate(selected_year, 12, 31))
        self.date_hasta.setDisplayFormat("dd/MM/yyyy")
        self.date_hasta.dateChanged.connect(self.cargar_requisiciones)
        
        filtro_layout.addWidget(lbl_desde)
        filtro_layout.addWidget(self.date_desde)
        filtro_layout.addWidget(lbl_hasta)
        filtro_layout.addWidget(self.date_hasta)
        filtro_layout.addStretch()
        
        # Contador
        self.lbl_contador = QLabel()
        self.lbl_contador.setStyleSheet("color: #666; font-size: 11px;")
        
        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Número", "Destino", "Solicitante", "Productos", "Acciones"
        ])
        
        self.tabla.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f1f3f4;
                padding: 10px;
                font-weight: bold;
            }
        """)
        
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(5, 100)
        
        self.tabla.setAlternatingRowColors(True)
        
        layout.addLayout(header_layout)
        layout.addLayout(filtro_layout)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)
        
        self.setLayout(layout)
    
    def cargar_requisiciones(self):
        """Carga las requisiciones"""
        self.session.expire_all()
        fecha_desde = self.date_desde.date().toPyDate()
        fecha_hasta = self.date_hasta.date().toPyDate()
        
        requisiciones = self.session.query(Requisicion).filter(
            Requisicion.fecha >= fecha_desde,
            Requisicion.fecha <= fecha_hasta
        ).order_by(Requisicion.fecha.desc()).all()
        
        self.mostrar_requisiciones(requisiciones)
    
    def mostrar_requisiciones(self, requisiciones):
        """Muestra requisiciones en la tabla"""
        self.requisiciones_mostradas = requisiciones
        self.tabla.setRowCount(len(requisiciones))
        
        for row, req in enumerate(requisiciones):
            self.tabla.setItem(row, 0, QTableWidgetItem(req.fecha.strftime('%d/%m/%Y')))
            self.tabla.setItem(row, 1, QTableWidgetItem(req.numero_requisicion))
            self.tabla.setItem(row, 2, QTableWidgetItem(req.destino.nombre))
            self.tabla.setItem(row, 3, QTableWidgetItem(req.solicitante or "-"))
            
            # Contar productos
            cant_productos = len(req.detalles)
            self.tabla.setItem(row, 4, QTableWidgetItem(str(cant_productos)))
            
            # Botón ver
            btn_ver = QPushButton()
            style_button(btn_ver, 'view', "Ver")
            btn_ver.clicked.connect(lambda checked, r=req: self.ver_detalle(r))

            btn_editar = QPushButton()
            style_button(btn_editar, 'edit', "Editar")
            btn_editar.clicked.connect(lambda checked, r=req: self.editar_requisicion(r))

            # Layout for buttons
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(5)
            btn_layout.addWidget(btn_ver)
            btn_layout.addWidget(btn_editar)

            btn_eliminar = QPushButton()
            style_button(btn_eliminar, 'delete', "Eliminar")
            btn_eliminar.clicked.connect(lambda checked, r=req: self.eliminar_requisicion(r))
            btn_layout.addWidget(btn_eliminar)

            btn_layout.addStretch()
            
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)

            self.tabla.setCellWidget(row, 5, btn_widget)
        
        self.lbl_contador.setText(f"📊 Total: {len(requisiciones)} requisición(es)")
    
    def nueva_requisicion(self):
        """Abre diálogo para nueva requisición"""
        dialog = RequisicionDialog(self, self.user_info)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_requisiciones()

    def editar_requisicion(self, requisicion):
        """Abre el diálogo para editar una requisición existente."""
        dialog = RequisicionDialog(self, self.user_info, requisicion_a_editar=requisicion)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_requisiciones()

    def eliminar_requisicion(self, requisicion):
        """Elimina una requisición y revierte los movimientos de stock."""
        confirmar = QMessageBox.warning(
            self, "Confirmar Eliminación",
            f"¿Está seguro de eliminar la requisición {requisicion.numero_requisicion}?\n\n"
            "Esta acción revertirá los movimientos de stock asociados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirmar == QMessageBox.StandardButton.No:
            return

        try:
            # Revertir cada movimiento
            for detalle in requisicion.detalles:
                almacen = self.session.get(Almacen, detalle.almacen_id)
                empresa = self.session.get(Empresa, almacen.empresa_id)

                costo_unitario, costo_total = self.kardex_manager.calcular_costo_salida(
                    empresa.id, detalle.producto_id, detalle.almacen_id, float(detalle.cantidad)
                )

                self.kardex_manager.registrar_movimiento(
                    empresa_id=almacen.empresa_id,
                    producto_id=detalle.producto_id,
                    almacen_id=detalle.almacen_id,
                    tipo=TipoMovimiento.DEVOLUCION_REQUISICION,
                    cantidad_entrada=detalle.cantidad,
                    cantidad_salida=0,
                    costo_unitario=costo_unitario,
                    costo_total=costo_total,
                    numero_documento=requisicion.numero_requisicion,
                    fecha_documento=requisicion.fecha,
                    observaciones=f"Reversión por eliminación de Requisición ID {requisicion.id}"
                )

            # Eliminar detalles y la requisición
            self.session.query(RequisicionDetalle).filter_by(requisicion_id=requisicion.id).delete()
            self.session.delete(requisicion)
            self.session.commit()

            QMessageBox.information(self, "Éxito", "Requisición eliminada y stock revertido.")
            self.cargar_requisiciones()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo eliminar la requisición:\n{e}")
    
    def ver_detalle(self, requisicion):
        """Muestra el detalle de la requisición"""
        # Volvemos a consultar la requisición y sus detalles en la sesión
        # para asegurarnos de que las relaciones (destino, detalles, producto, etc.)
        # están cargadas.
        req = self.session.query(Requisicion).options(
            joinedload(Requisicion.destino),
            joinedload(Requisicion.detalles).joinedload(RequisicionDetalle.producto),
            joinedload(Requisicion.detalles).joinedload(RequisicionDetalle.almacen)
        ).filter_by(id=requisicion.id).first()

        if not req:
            QMessageBox.warning(self, "Error", "No se encontró la requisición.")
            return
            
        detalles = req.detalles
        
        # Corregimos la línea incompleta y completamos el mensaje
        mensaje = f"<b>REQUISICIÓN: {req.numero_requisicion}</b><br>"
        mensaje += f"Fecha: {req.fecha.strftime('%d/%m/%Y')}<br>"
        mensaje += f"Destino: {req.destino.nombre}<br>"
        mensaje += f"Solicitante: {req.solicitante or '-'}<br><br>"
        
        mensaje += "<b>Detalles de Productos:</b><br>"
        mensaje += "<ul>"
        
        if not detalles:
            mensaje += "<li>No se encontraron productos en esta requisición.</li>"

        for det in detalles:
            # Asumiendo que las relaciones 'producto' y 'almacen' están cargadas
            producto_info = f"{det.producto.codigo} - {det.producto.nombre}"
            almacen_info = det.almacen.nombre
            mensaje += f"<li><b>{det.cantidad}</b> x [{producto_info}] (Del Almacén: {almacen_info})</li>"
        
        mensaje += "</ul>"
        
        if req.observaciones:
            mensaje += f"<br><b>Observaciones:</b><br>{req.observaciones}"

        # Mostramos el mensaje en un QMessageBox (ya estaba importado)
        QMessageBox.information(self, "Detalle de Requisición", mensaje)

# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    ventana = RequisicionesWindow()
    ventana.resize(1200, 700)
    ventana.show()

    sys.exit(app.exec())
