from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QDialog, QMessageBox, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QIcon
from models.database_model import (obtener_session, Cotizacion, CotizacionDetalle, 
                                   EstadoCotizacion, Cliente, Producto, Moneda)
from views.ventas_window import VentaDialog
from utils.styles import STYLE_TABLE_ALTERNATE
from datetime import datetime

class CotizacionesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.cargar_datos()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("📝 Gestión de Cotizaciones")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a73e8;")
        
        btn_nueva = QPushButton("Nueva Cotización")
        btn_nueva.setStyleSheet("background-color: #1a73e8; color: white; padding: 8px 15px; border-radius: 4px;")
        btn_nueva.clicked.connect(self.nueva_cotizacion)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_nueva)
        layout.addLayout(header_layout)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels(["ID", "Fecha", "Cliente", "Total", "Estado", "Acciones", ""])
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setStyleSheet(STYLE_TABLE_ALTERNATE)
        layout.addWidget(self.tabla)

        self.setLayout(layout)

    def cargar_datos(self):
        self.tabla.setRowCount(0)
        cotizaciones = self.session.query(Cotizacion).order_by(Cotizacion.fecha_emision.desc()).all()
        
        for row, cot in enumerate(cotizaciones):
            self.tabla.insertRow(row)
            self.tabla.setItem(row, 0, QTableWidgetItem(cot.numero_cotizacion))
            self.tabla.setItem(row, 1, QTableWidgetItem(str(cot.fecha_emision)))
            self.tabla.setItem(row, 2, QTableWidgetItem(cot.cliente.razon_social_o_nombre if cot.cliente else "S/N"))
            
            simbolo = "S/" if cot.moneda == Moneda.SOLES else "$"
            self.tabla.setItem(row, 3, QTableWidgetItem(f"{simbolo} {cot.total:,.2f}"))
            
            item_estado = QTableWidgetItem(cot.estado.value)
            if cot.estado == EstadoCotizacion.APROBADA:
                item_estado.setForeground(Qt.GlobalColor.darkGreen)
            elif cot.estado == EstadoCotizacion.CONVERTIDA_VENTA:
                item_estado.setForeground(Qt.GlobalColor.blue)
            self.tabla.setItem(row, 4, item_estado)

            # Botones
            btn_ver = QPushButton("Ver/Editar")
            btn_ver.clicked.connect(lambda checked, c=cot: self.editar_cotizacion(c))
            self.tabla.setCellWidget(row, 5, btn_ver)

            if cot.estado == EstadoCotizacion.APROBADA:
                btn_convertir = QPushButton("Convertir a Venta")
                btn_convertir.setStyleSheet("background-color: #34a853; color: white;")
                btn_convertir.clicked.connect(lambda checked, c=cot: self.convertir_a_venta(c))
                self.tabla.setCellWidget(row, 6, btn_convertir)

    def nueva_cotizacion(self):
        dialog = CotizacionDialog(self)
        if dialog.exec():
            self.cargar_datos()

    def editar_cotizacion(self, cotizacion):
        dialog = CotizacionDialog(self, cotizacion)
        if dialog.exec():
            self.cargar_datos()

    def convertir_a_venta(self, cotizacion):
        reply = QMessageBox.question(self, "Confirmar", 
                                     f"¿Desea convertir la cotización {cotizacion.numero_cotizacion} en una Venta?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Abrir diálogo de venta pre-llenado
            # Nota: Esto requiere que VentaDialog acepte datos externos o una instancia de cotización
            # Para simplificar, pasaremos los datos básicos al init o usaremos un método helper
            
            # Simulamos pasar los detalles
            detalles_venta = []
            for det in cotizacion.detalles:
                detalles_venta.append(det) # Objeto CotizacionDetalle compatible en estructura básica

            dialog_venta = VentaDialog(self, venta_a_editar=None, detalles_originales=detalles_venta)
            
            # Pre-llenar UI de VentaDialog (esto es un hack si VentaDialog no está preparado)
            # Idealmente VentaDialog debería tener un método `cargar_desde_cotizacion`
            # Por ahora, lo haremos manualmente accediendo a los widgets públicos
            
            dialog_venta.cmb_doc_cliente.setCurrentIndex(dialog_venta.cmb_doc_cliente.findData(cotizacion.cliente_id))
            dialog_venta.txt_observaciones.setPlainText(f"Basado en Cotización {cotizacion.numero_cotizacion}. {cotizacion.observaciones or ''}")
            
            if dialog_venta.exec():
                cotizacion.estado = EstadoCotizacion.CONVERTIDA_VENTA
                self.session.commit()
                self.cargar_datos()

# --- DIALOGO DE COTIZACIÓN (Simplificado, reutilizando lógica de Venta si fuera posible, pero haremos uno propio rápido) ---
# Por brevedad, este diálogo será básico. En producción debería heredar de una clase base común con VentaDialog.

from PyQt6.QtWidgets import QFormLayout, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox

class CotizacionDialog(QDialog):
    def __init__(self, parent=None, cotizacion=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.cotizacion = cotizacion
        self.detalles = []
        self.init_ui()
        if cotizacion:
            self.cargar_datos()

    def init_ui(self):
        self.setWindowTitle("Nueva Cotización" if not self.cotizacion else f"Editar Cotización {self.cotizacion.numero_cotizacion}")
        self.setMinimumSize(800, 600)
        layout = QVBoxLayout(self)

        # Formulario Cabecera
        form = QFormLayout()
        
        self.txt_numero = QLabel("Auto-generado")
        if self.cotizacion: self.txt_numero.setText(self.cotizacion.numero_cotizacion)
        
        self.cmb_cliente = QComboBox()
        clientes = self.session.query(Cliente).filter_by(activo=True).all()
        for c in clientes:
            self.cmb_cliente.addItem(c.razon_social_o_nombre, c.id)
            
        self.date_emision = QDateEdit(QDate.currentDate())
        self.date_emision.setCalendarPopup(True)
        
        self.cmb_estado = QComboBox()
        for est in EstadoCotizacion:
            self.cmb_estado.addItem(est.value, est)

        form.addRow("Número:", self.txt_numero)
        form.addRow("Cliente:", self.cmb_cliente)
        form.addRow("Fecha:", self.date_emision)
        form.addRow("Estado:", self.cmb_estado)
        
        layout.addLayout(form)

        # Tabla Detalles (Simplificada)
        self.tabla_det = QTableWidget()
        self.tabla_det.setColumnCount(4)
        self.tabla_det.setHorizontalHeaderLabels(["Producto", "Cant", "Precio", "Subtotal"])
        layout.addWidget(self.tabla_det)
        
        # Botones Agregar Producto (Placeholder)
        btn_add = QPushButton("Agregar Producto (Simulado)")
        btn_add.clicked.connect(self.agregar_producto_simulado)
        layout.addWidget(btn_add)

        # Botones Guardar
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.guardar)
        layout.addWidget(btn_save)

    def agregar_producto_simulado(self):
        # En una implementación real, esto abriría un buscador de productos
        prod = self.session.query(Producto).first()
        if prod:
            row = self.tabla_det.rowCount()
            self.tabla_det.insertRow(row)
            self.tabla_det.setItem(row, 0, QTableWidgetItem(prod.nombre))
            self.tabla_det.setItem(row, 1, QTableWidgetItem("1"))
            self.tabla_det.setItem(row, 2, QTableWidgetItem("100.00"))
            self.tabla_det.setItem(row, 3, QTableWidgetItem("100.00"))
            
            self.detalles.append({
                "producto_id": prod.id,
                "cantidad": 1,
                "precio": 100.0,
                "subtotal": 100.0
            })

    def cargar_datos(self):
        self.cmb_cliente.setCurrentIndex(self.cmb_cliente.findData(self.cotizacion.cliente_id))
        self.date_emision.setDate(self.cotizacion.fecha_emision)
        self.cmb_estado.setCurrentIndex(self.cmb_estado.findData(self.cotizacion.estado))
        
        # Cargar detalles...

    def guardar(self):
        try:
            if not self.cotizacion:
                count = self.session.query(Cotizacion).count()
                numero = f"COT-{count+1:04d}"
                self.cotizacion = Cotizacion(numero_cotizacion=numero)
                self.session.add(self.cotizacion)
            
            self.cotizacion.cliente_id = self.cmb_cliente.currentData()
            self.cotizacion.fecha_emision = self.date_emision.date().toPyDate()
            self.cotizacion.estado = self.cmb_estado.currentData()
            self.cotizacion.subtotal = sum(d['subtotal'] for d in self.detalles)
            self.cotizacion.total = self.cotizacion.subtotal * 1.18 # IGV hardcoded for demo
            
            # Guardar detalles...
            
            self.session.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
