from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QDialog, QFormLayout, QHeaderView, QGroupBox, QMessageBox,
                             QComboBox, QDateEdit, QTextEdit, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from models.database_model import (obtener_session, OrdenMantenimiento, Equipo, 
                                   TipoMantenimiento, EstadoMantenimiento, EstadoEquipo)
from utils.widgets import SearchableComboBox
from datetime import date, datetime

class OrdenMantenimientoDialog(QDialog):
    orden_guardada = pyqtSignal()

    def __init__(self, parent=None, orden=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.orden = orden
        self.init_ui()
        if orden:
            self.cargar_datos()

    def init_ui(self):
        self.setWindowTitle("Orden de Mantenimiento")
        self.setFixedSize(500, 450)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.cmb_equipo = SearchableComboBox()
        self.cargar_equipos()
        form.addRow("Equipo:*", self.cmb_equipo)
        
        self.cmb_tipo = QComboBox()
        for t in TipoMantenimiento:
            self.cmb_tipo.addItem(t.value, t)
        form.addRow("Tipo:", self.cmb_tipo)
        
        self.date_ingreso = QDateEdit(date.today())
        self.date_ingreso.setCalendarPopup(True)
        form.addRow("Fecha Ingreso:", self.date_ingreso)
        
        self.date_estimada = QDateEdit(date.today())
        self.date_estimada.setCalendarPopup(True)
        form.addRow("Fecha Est. Salida:", self.date_estimada)
        
        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(80)
        form.addRow("Descripción:", self.txt_descripcion)
        
        self.txt_realizado_por = QTextEdit() # O LineEdit
        self.txt_realizado_por.setMaximumHeight(30)
        self.txt_realizado_por.setPlaceholderText("Técnico o Proveedor")
        form.addRow("Realizado por:", self.txt_realizado_por)
        
        self.spn_costo = QDoubleSpinBox()
        self.spn_costo.setRange(0, 999999)
        self.spn_costo.setPrefix("S/ ")
        form.addRow("Costo Total:", self.spn_costo)
        
        self.cmb_estado = QComboBox()
        for e in EstadoMantenimiento:
            self.cmb_estado.addItem(e.value, e)
        form.addRow("Estado:", self.cmb_estado)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.guardar)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def cargar_equipos(self):
        equipos = self.session.query(Equipo).filter(Equipo.activo == True).all()
        for eq in equipos:
            self.cmb_equipo.addItem(f"{eq.codigo} - {eq.nombre}", eq.id)

    def cargar_datos(self):
        index = self.cmb_equipo.findData(self.orden.equipo_id)
        if index >= 0: self.cmb_equipo.setCurrentIndex(index)
        self.cmb_equipo.setEnabled(False)
        
        index_tipo = self.cmb_tipo.findData(self.orden.tipo)
        if index_tipo >= 0: self.cmb_tipo.setCurrentIndex(index_tipo)
        
        self.date_ingreso.setDate(self.orden.fecha_ingreso)
        if self.orden.fecha_estimada_salida:
            self.date_estimada.setDate(self.orden.fecha_estimada_salida)
            
        self.txt_descripcion.setPlainText(self.orden.descripcion or "")
        self.txt_realizado_por.setPlainText(self.orden.realizado_por or "") # Using QTextEdit as LineEdit wrapper
        self.spn_costo.setValue(self.orden.costo_total)
        
        index_est = self.cmb_estado.findData(self.orden.estado)
        if index_est >= 0: self.cmb_estado.setCurrentIndex(index_est)

    def guardar(self):
        equipo_id = self.cmb_equipo.currentData()
        if not equipo_id:
            QMessageBox.warning(self, "Error", "Seleccione un equipo.")
            return
            
        try:
            if not self.orden:
                self.orden = OrdenMantenimiento(equipo_id=equipo_id)
                self.session.add(self.orden)
                
                # Update Equipo status
                equipo = self.session.query(Equipo).get(equipo_id)
                equipo.estado = EstadoEquipo.MANTENIMIENTO
            
            self.orden.tipo = self.cmb_tipo.currentData()
            self.orden.fecha_ingreso = self.date_ingreso.date().toPyDate()
            self.orden.fecha_estimada_salida = self.date_estimada.date().toPyDate()
            self.orden.descripcion = self.txt_descripcion.toPlainText()
            self.orden.realizado_por = self.txt_realizado_por.toPlainText()
            self.orden.costo_total = self.spn_costo.value()
            self.orden.estado = self.cmb_estado.currentData()
            
            # Si finaliza, liberar equipo
            if self.orden.estado == EstadoMantenimiento.FINALIZADO:
                self.orden.fecha_real_salida = date.today()
                if self.orden.equipo.estado == EstadoEquipo.MANTENIMIENTO:
                    self.orden.equipo.estado = EstadoEquipo.DISPONIBLE
                    # Update maintenance date on equipment
                    self.orden.equipo.fecha_ultima_calibracion = date.today() # Or maintenance date
            
            self.session.commit()
            self.orden_guardada.emit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class MaintenanceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.cargar_datos()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        title = QLabel("🔧 Gestión de Mantenimiento")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        btn_new = QPushButton("Nueva Orden")
        btn_new.clicked.connect(self.nueva_orden)
        btn_new.setStyleSheet("background-color: #3498db; color: white;")
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_new)
        layout.addLayout(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Equipo", "Tipo", "Ingreso", "Est. Salida", "Estado", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.setLayout(layout)

    def cargar_datos(self):
        self.table.setRowCount(0)
        ordenes = self.session.query(OrdenMantenimiento).order_by(OrdenMantenimiento.fecha_ingreso.desc()).all()
        
        for row, orden in enumerate(ordenes):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(orden.id)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{orden.equipo.codigo} - {orden.equipo.nombre}"))
            self.table.setItem(row, 2, QTableWidgetItem(orden.tipo.value))
            self.table.setItem(row, 3, QTableWidgetItem(orden.fecha_ingreso.strftime("%d/%m/%Y")))
            self.table.setItem(row, 4, QTableWidgetItem(orden.fecha_estimada_salida.strftime("%d/%m/%Y") if orden.fecha_estimada_salida else "-"))
            
            item_est = QTableWidgetItem(orden.estado.value)
            if orden.estado == EstadoMantenimiento.PENDIENTE:
                item_est.setForeground(Qt.GlobalColor.red)
            elif orden.estado == EstadoMantenimiento.EN_PROCESO:
                item_est.setForeground(Qt.GlobalColor.blue)
            else:
                item_est.setForeground(Qt.GlobalColor.green)
            self.table.setItem(row, 5, item_est)
            
            btn_edit = QPushButton("Editar")
            btn_edit.clicked.connect(lambda checked, o=orden: self.editar_orden(o))
            self.table.setCellWidget(row, 6, btn_edit)

    def nueva_orden(self):
        dialog = OrdenMantenimientoDialog(self)
        dialog.orden_guardada.connect(self.cargar_datos)
        dialog.exec()

    def editar_orden(self, orden):
        dialog = OrdenMantenimientoDialog(self, orden)
        dialog.orden_guardada.connect(self.cargar_datos)
        dialog.exec()
