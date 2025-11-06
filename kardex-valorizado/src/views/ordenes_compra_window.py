"""
Gestión de Órdenes de Compra - Sistema Kardex Valorizado
Archivo: src/views/ordenes_compra_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox,
                              QTextEdit, QMessageBox, QDialog, QFormLayout, 
                              QHeaderView, QGroupBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, OrdenCompra, OrdenCompraDetalle,
                                   Proveedor, Producto, Empresa, TipoCambio,
                                   Moneda, EstadoOrden, Usuario)


class OrdenCompraDialog(QDialog):
    """Diálogo para crear/editar órdenes de compra"""
    
    def __init__(self, parent=None, user_info=None, orden=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.user_info = user_info
        self.orden = orden
        self.detalles = []
        self.init_ui()
        self.cargar_datos_iniciales()
        
        if orden:
            self.cargar_orden()
    
    def init_ui(self):
        self.setWindowTitle("Nueva Orden de Compra" if not self.orden else "Ver Orden de Compra")
        self.setMinimumSize(900, 650)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox, QTextEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
                background-color: white;
                color: black;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #1a73e8;
                selection-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        titulo = QLabel("📋 " + ("Nueva Orden de Compra" if not self.orden else f"Orden {self.orden.numero_orden}"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)
        
        # Datos de la orden
        grupo_orden = QGroupBox("Datos de la Orden")
        form_orden = QFormLayout()
        
        # Empresa y Proveedor
        fila1 = QHBoxLayout()
        
        fila1.addWidget(QLabel("Empresa:"))
        self.cmb_empresa = QComboBox()
        self.cmb_empresa.setMinimumWidth(250)
        fila1.addWidget(self.cmb_empresa, 2)
        
        fila1.addWidget(QLabel("Proveedor:"))
        self.cmb_proveedor = QComboBox()
        self.cmb_proveedor.setMinimumWidth(300)
        fila1.addWidget(self.cmb_proveedor, 3)
        
        form_orden.addRow("", fila1)
        
        # Número y Fecha
        fila2 = QHBoxLayout()
        
        self.txt_numero = QLineEdit()
        self.txt_numero.setPlaceholderText("Ej: OC-2024-0001")
        
        self.date_fecha = QDateEdit()
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.setDate(QDate.currentDate())
        self.date_fecha.setDisplayFormat("dd/MM/yyyy")
        self.date_fecha.dateChanged.connect(self.actualizar_tipo_cambio)
        
        fila2.addWidget(QLabel("Número:"))
        fila2.addWidget(self.txt_numero)
        fila2.addWidget(QLabel("Fecha:"))
        fila2.addWidget(self.date_fecha)
        fila2.addStretch()
        
        form_orden.addRow("", fila2)
        
        # Moneda y TC
        fila3 = QHBoxLayout()
        
        self.cmb_moneda = QComboBox()
        self.cmb_moneda.addItem("SOLES (S/)", Moneda.SOLES.value)
        self.cmb_moneda.addItem("DÓLARES ($)", Moneda.DOLARES.value)
        self.cmb_moneda.currentIndexChanged.connect(self.moneda_cambiada)
        
        self.spn_tipo_cambio = QDoubleSpinBox()
        self.spn_tipo_cambio.setRange(0.001, 99.999)
        self.spn_tipo_cambio.setDecimals(3)
        self.spn_tipo_cambio.setValue(1.000)
        self.spn_tipo_cambio.setEnabled(False)
        
        fila3.addWidget(QLabel("Moneda:"))
        fila3.addWidget(self.cmb_moneda)
        fila3.addWidget(QLabel("Tipo Cambio:"))
        fila3.addWidget(self.spn_tipo_cambio)
        fila3.addStretch()
        
        form_orden.addRow("", fila3)
        
        grupo_orden.setLayout(form_orden)
        layout.addWidget(grupo_orden)
        
        # Productos
        grupo_productos = QGroupBox("Productos")
        productos_layout = QVBoxLayout()
        
        # Selector
        selector_layout = QHBoxLayout()
        
        self.cmb_producto = QComboBox()
        self.cmb_producto.setMinimumWidth(300)
        
        self.spn_cantidad = QDoubleSpinBox()
        self.spn_cantidad.setRange(0.01, 999999)
        self.spn_cantidad.setDecimals(2)
        self.spn_cantidad.setValue(1.00)
        
        self.spn_precio = QDoubleSpinBox()
        self.spn_precio.setRange(0.01, 999999.99)
        self.spn_precio.setDecimals(2)
        
        btn_agregar = QPushButton("+ Agregar")
        btn_agregar.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        btn_agregar.clicked.connect(self.agregar_producto)
        
        selector_layout.addWidget(QLabel("Producto:"))
        selector_layout.addWidget(self.cmb_producto, 2)
        selector_layout.addWidget(QLabel("Cant:"))
        selector_layout.addWidget(self.spn_cantidad)
        selector_layout.addWidget(QLabel("Precio:"))
        selector_layout.addWidget(self.spn_precio)
        selector_layout.addWidget(btn_agregar)
        
        productos_layout.addLayout(selector_layout)
        
        # Tabla productos
        self.tabla_productos = QTableWidget()
        self.tabla_productos.setColumnCount(5)
        self.tabla_productos.setHorizontalHeaderLabels([
            "Producto", "Cantidad", "Precio Unit.", "Subtotal", "Acción"
        ])
        self.tabla_productos.setMaximumHeight(180)
        
        header = self.tabla_productos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tabla_productos.setColumnWidth(4, 80)
        
        productos_layout.addWidget(self.tabla_productos)
        
        grupo_productos.setLayout(productos_layout)
        layout.addWidget(grupo_productos)
        
        # Total
        self.lbl_total = QLabel("TOTAL: S/ 0.00")
        self.lbl_total.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1a73e8;
            padding: 10px;
            background-color: #e8f0fe;
            border-radius: 5px;
        """)
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.lbl_total)
        
        # Observaciones
        layout.addWidget(QLabel("Observaciones:"))
        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setMaximumHeight(60)
        layout.addWidget(self.txt_observaciones)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("padding: 10px 30px; background-color: #f1f3f4;")
        btn_cancelar.clicked.connect(self.reject)
        
        self.btn_guardar = QPushButton("Guardar Orden")
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.btn_guardar.clicked.connect(self.guardar_orden)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def cargar_datos_iniciales(self):
        """Carga empresas, proveedores y productos"""
        # Empresas
        empresas = self.session.query(Empresa).filter_by(activo=True).all()
        for emp in empresas:
            self.cmb_empresa.addItem(f"{emp.ruc} - {emp.razon_social}", emp.id)
        
        # Proveedores
        proveedores = self.session.query(Proveedor).filter_by(activo=True).all()
        for prov in proveedores:
            self.cmb_proveedor.addItem(f"{prov.ruc} - {prov.razon_social}", prov.id)
        
        # Productos
        productos = self.session.query(Producto).filter_by(activo=True).all()
        for prod in productos:
            self.cmb_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)
    
    def cargar_orden(self):
        """Carga datos de orden existente"""
        # Seleccionar empresa
        for i in range(self.cmb_empresa.count()):
            if self.cmb_empresa.itemData(i) == self.orden.empresa_id:
                self.cmb_empresa.setCurrentIndex(i)
                break
        
        # Seleccionar proveedor
        for i in range(self.cmb_proveedor.count()):
            if self.cmb_proveedor.itemData(i) == self.orden.proveedor_id:
                self.cmb_proveedor.setCurrentIndex(i)
                break
        
        self.txt_numero.setText(self.orden.numero_orden)
        self.txt_numero.setEnabled(False)
        
        self.date_fecha.setDate(QDate(
            self.orden.fecha.year,
            self.orden.fecha.month,
            self.orden.fecha.day
        ))
        
        # Moneda
        for i in range(self.cmb_moneda.count()):
            if self.cmb_moneda.itemData(i) == self.orden.moneda.value:
                self.cmb_moneda.setCurrentIndex(i)
                break
        
        self.spn_tipo_cambio.setValue(self.orden.tipo_cambio)
        self.txt_observaciones.setPlainText(self.orden.observaciones or "")
        
        # Cargar detalles
        detalles = self.session.query(OrdenCompraDetalle).filter_by(orden_id=self.orden.id).all()
        for det in detalles:
            producto = self.session.query(Producto).get(det.producto_id)
            self.detalles.append({
                'producto_id': det.producto_id,
                'producto_nombre': f"{producto.codigo} - {producto.nombre}",
                'cantidad': det.cantidad,
                'precio_unitario': det.precio_unitario,
                'subtotal': det.subtotal
            })
        
        self.actualizar_tabla_productos()
        self.recalcular_total()
        
        # Deshabilitar edición si no es pendiente
        if self.orden.estado != EstadoOrden.PENDIENTE:
            self.setWindowTitle(f"Ver Orden {self.orden.numero_orden} - {self.orden.estado.value}")
            self.cmb_empresa.setEnabled(False)
            self.cmb_proveedor.setEnabled(False)
            self.cmb_moneda.setEnabled(False)
            self.spn_tipo_cambio.setEnabled(False)
            self.cmb_producto.setEnabled(False)
            self.spn_cantidad.setEnabled(False)
            self.spn_precio.setEnabled(False)
            self.txt_observaciones.setEnabled(False)
            self.btn_guardar.setEnabled(False)
    
    def moneda_cambiada(self):
        """Cuando cambia la moneda"""
        es_dolares = self.cmb_moneda.currentData() == Moneda.DOLARES.value
        self.spn_tipo_cambio.setEnabled(es_dolares)
        
        if es_dolares:
            self.actualizar_tipo_cambio()
        else:
            self.spn_tipo_cambio.setValue(1.000)
        
        self.recalcular_total()
    
    def actualizar_tipo_cambio(self):
        """Actualiza tipo de cambio según fecha"""
        if self.cmb_moneda.currentData() != Moneda.DOLARES.value:
            return
        
        fecha = self.date_fecha.date().toPyDate()
        tc = self.session.query(TipoCambio).filter_by(fecha=fecha).first()
        
        if tc:
            self.spn_tipo_cambio.setValue(tc.precio_venta)
    
    def agregar_producto(self):
        """Agrega producto a la orden"""
        prod_id = self.cmb_producto.currentData()
        cantidad = self.spn_cantidad.value()
        precio = self.spn_precio.value()
        
        if not prod_id or cantidad <= 0 or precio <= 0:
            QMessageBox.warning(self, "Error", "Complete todos los campos del producto")
            return
        
        producto = self.session.query(Producto).get(prod_id)
        
        self.detalles.append({
            'producto_id': prod_id,
            'producto_nombre': f"{producto.codigo} - {producto.nombre}",
            'cantidad': cantidad,
            'precio_unitario': precio,
            'subtotal': cantidad * precio
        })
        
        self.actualizar_tabla_productos()
        self.recalcular_total()
        
        # Limpiar
        self.spn_cantidad.setValue(1.00)
        self.spn_precio.setValue(0.00)
    
    def actualizar_tabla_productos(self):
        """Actualiza tabla de productos"""
        self.tabla_productos.setRowCount(len(self.detalles))
        
        for row, det in enumerate(self.detalles):
            self.tabla_productos.setItem(row, 0, QTableWidgetItem(det['producto_nombre']))
            self.tabla_productos.setItem(row, 1, QTableWidgetItem(f"{det['cantidad']:.2f}"))
            self.tabla_productos.setItem(row, 2, QTableWidgetItem(f"{det['precio_unitario']:.2f}"))
            self.tabla_productos.setItem(row, 3, QTableWidgetItem(f"{det['subtotal']:.2f}"))
            
            btn_eliminar = QPushButton("✕")
            btn_eliminar.setStyleSheet("background-color: #ea4335; color: white;")
            btn_eliminar.clicked.connect(lambda checked, r=row: self.eliminar_producto(r))
            self.tabla_productos.setCellWidget(row, 4, btn_eliminar)
    
    def eliminar_producto(self, row):
        """Elimina producto de la lista"""
        if 0 <= row < len(self.detalles):
            del self.detalles[row]
            self.actualizar_tabla_productos()
            self.recalcular_total()
    
    def recalcular_total(self):
        """Recalcula el total"""
        total = sum(det['subtotal'] for det in self.detalles)
        moneda_simbolo = "S/" if self.cmb_moneda.currentData() == Moneda.SOLES.value else "$"
        self.lbl_total.setText(f"TOTAL: {moneda_simbolo} {total:.2f}")
    
    def guardar_orden(self):
        """Guarda la orden de compra"""
        if not self.cmb_empresa.currentData() or not self.cmb_proveedor.currentData():
            QMessageBox.warning(self, "Error", "Seleccione empresa y proveedor")
            return
        
        if not self.txt_numero.text().strip():
            QMessageBox.warning(self, "Error", "Ingrese número de orden")
            return
        
        if not self.detalles:
            QMessageBox.warning(self, "Error", "Agregue al menos un producto")
            return
        
        try:
            if not self.orden:
                # Crear nueva
                orden = OrdenCompra(
                    empresa_id=self.cmb_empresa.currentData(),
                    proveedor_id=self.cmb_proveedor.currentData(),
                    numero_orden=self.txt_numero.text().strip(),
                    fecha=self.date_fecha.date().toPyDate(),
                    moneda=Moneda(self.cmb_moneda.currentData()),
                    tipo_cambio=self.spn_tipo_cambio.value(),
                    observaciones=self.txt_observaciones.toPlainText() or None,
                    estado=EstadoOrden.PENDIENTE
                )
                
                self.session.add(orden)
                self.session.flush()
                
                # Agregar detalles
                for det in self.detalles:
                    detalle = OrdenCompraDetalle(
                        orden_id=orden.id,
                        producto_id=det['producto_id'],
                        cantidad=det['cantidad'],
                        cantidad_recibida=0,
                        precio_unitario=det['precio_unitario'],
                        subtotal=det['subtotal']
                    )
                    self.session.add(detalle)
                
                self.session.commit()
                
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Orden {orden.numero_orden} creada exitosamente\n\n"
                    f"Estado: PENDIENTE\n"
                    f"Productos: {len(self.detalles)}"
                )
                
                self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")


class OrdenesCompraWindow(QWidget):
    """Ventana principal de órdenes de compra"""
    
    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.init_ui()
        self.cargar_ordenes()
    
    def init_ui(self):
        self.setWindowTitle("Gestión de Órdenes de Compra")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("📋 Órdenes de Compra")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        btn_nueva = QPushButton("+ Nueva Orden")
        btn_nueva.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        btn_nueva.clicked.connect(self.nueva_orden)
        
        if self.user_info and self.user_info.get('licencia_vencida'):
            btn_nueva.setEnabled(False)
        
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nueva)
        
        # Filtros
        filtro_layout = QHBoxLayout()
        
        self.cmb_estado_filtro = QComboBox()
        self.cmb_estado_filtro.addItem("Todos los estados", None)
        self.cmb_estado_filtro.addItem("🟡 Pendiente", EstadoOrden.PENDIENTE.value)
        self.cmb_estado_filtro.addItem("🟠 Parcial", EstadoOrden.PARCIAL.value)
        self.cmb_estado_filtro.addItem("🟢 Completa", EstadoOrden.COMPLETA.value)
        self.cmb_estado_filtro.addItem("🔴 Anulada", EstadoOrden.ANULADA.value)
        self.cmb_estado_filtro.currentIndexChanged.connect(self.cargar_ordenes)
        
        filtro_layout.addWidget(self.cmb_estado_filtro)
        filtro_layout.addStretch()
        
        # Contador
        self.lbl_contador = QLabel()
        self.lbl_contador.setStyleSheet("color: #666; font-size: 11px;")
        
        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "Número", "Fecha", "Empresa", "Proveedor", "Estado", "Total", "Recibido", "Acciones"
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
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(7, 180)
        
        self.tabla.setAlternatingRowColors(True)
        
        layout.addLayout(header_layout)
        layout.addLayout(filtro_layout)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)
        
        self.setLayout(layout)
    
    def cargar_ordenes(self):
        """Carga las órdenes de compra"""
        estado_filtro = self.cmb_estado_filtro.currentData()
        
        query = self.session.query(OrdenCompra)
        
        if estado_filtro:
            query = query.filter_by(estado=EstadoOrden(estado_filtro))
        
        ordenes = query.order_by(OrdenCompra.fecha.desc()).all()
        
        self.mostrar_ordenes(ordenes)
    
    def mostrar_ordenes(self, ordenes):
        """Muestra órdenes en la tabla"""
        self.tabla.setRowCount(len(ordenes))
        
        for row, orden in enumerate(ordenes):
            self.tabla.setItem(row, 0, QTableWidgetItem(orden.numero_orden))
            self.tabla.setItem(row, 1, QTableWidgetItem(orden.fecha.strftime('%d/%m/%Y')))
            self.tabla.setItem(row, 2, QTableWidgetItem(orden.empresa.razon_social))
            self.tabla.setItem(row, 3, QTableWidgetItem(orden.proveedor.razon_social))
            
            # Estado con color
            estado_item = QTableWidgetItem(orden.estado.value)
            if orden.estado == EstadoOrden.PENDIENTE:
                estado_item.setForeground(QColor("#f9ab00"))
            elif orden.estado == EstadoOrden.PARCIAL:
                estado_item.setForeground(QColor("#ff9800"))
            elif orden.estado == EstadoOrden.COMPLETA:
                estado_item.setForeground(QColor("#34a853"))
            else:
                estado_item.setForeground(QColor("#ea4335"))
            self.tabla.setItem(row, 4, estado_item)
            
            # Total
            total = sum(det.subtotal for det in orden.detalles)
            moneda = "S/" if orden.moneda == Moneda.SOLES else "$"
            self.tabla.setItem(row, 5, QTableWidgetItem(f"{moneda} {total:.2f}"))
            
            # Porcentaje recibido
            total_cantidad = sum(det.cantidad for det in orden.detalles)
            total_recibido = sum(det.cantidad_recibida for det in orden.detalles)
            porcentaje = (total_recibido / total_cantidad * 100) if total_cantidad > 0 else 0
            self.tabla.setItem(row, 6, QTableWidgetItem(f"{porcentaje:.0f}%"))
            
            # Botones
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 5, 5, 5)
            
            btn_ver = QPushButton("Ver")
            btn_ver.setStyleSheet("background-color: #1a73e8; color: white; padding: 5px;")
            btn_ver.clicked.connect(lambda checked, o=orden: self.ver_orden(o))
            
            btn_convertir = QPushButton("→ Compra")
            btn_convertir.setStyleSheet("background-color: #34a853; color: white; padding: 5px;")
            btn_convertir.clicked.connect(lambda checked, o=orden: self.convertir_a_compra(o))
            btn_convertir.setEnabled(orden.estado == EstadoOrden.PENDIENTE)
            
            btn_layout.addWidget(btn_ver)
            btn_layout.addWidget(btn_convertir)
            btn_widget.setLayout(btn_layout)
            
            self.tabla.setCellWidget(row, 7, btn_widget)
        
        self.lbl_contador.setText(f"📊 Total: {len(ordenes)} orden(es)")
    
    def nueva_orden(self):
        """Crea nueva orden"""
        dialog = OrdenCompraDialog(self, self.user_info)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_ordenes()
    
    def ver_orden(self, orden):
        """Ver detalle de orden"""
        dialog = OrdenCompraDialog(self, self.user_info, orden)
        dialog.exec()
    
    def convertir_a_compra(self, orden):
        """Convierte la orden en compra"""
        QMessageBox.information(
            self,
            "Convertir a Compra",
            f"Para convertir la orden {orden.numero_orden} a compra:\n\n"
            "1. Ve a Operaciones → Compras\n"
            "2. Crea una nueva compra\n"
            "3. Usa los mismos datos de la orden\n\n"
            "Próximamente: Conversión automática"
        )


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    ventana = OrdenesCompraWindow()
    ventana.resize(1200, 700)
    ventana.show()
    
    sys.exit(app.exec())
