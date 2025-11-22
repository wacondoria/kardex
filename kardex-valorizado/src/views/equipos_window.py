from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidgetItem, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QMessageBox,
                             QComboBox, QCheckBox, QDateEdit, QDoubleSpinBox, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Equipo, Almacen, NivelEquipo, EstadoEquipo
from utils.widgets import SearchableComboBox, UpperLineEdit
from views.base_crud_view import BaseCRUDView

class EquipoDialog(QDialog):
    """Diálogo para crear/editar equipos"""
    
    equipo_guardado = pyqtSignal()

    def __init__(self, parent=None, equipo=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.equipo = equipo
        self.init_ui()
        
        if equipo:
            self.cargar_datos()

    def init_ui(self):
        self.setWindowTitle("Nuevo Equipo" if not self.equipo else "Editar Equipo")
        self.setFixedSize(700, 600)
        self.setStyleSheet("QDialog { background-color: #f5f5f5; }")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        titulo = QLabel("🚜 " + ("Nuevo Equipo" if not self.equipo else "Editar Equipo"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(titulo)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # --- CAMPOS ---
        self.txt_codigo = UpperLineEdit()
        self.txt_codigo.setPlaceholderText("Ej: MQ-315-A")
        form_layout.addRow("Código:*", self.txt_codigo)
        
        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre del equipo")
        form_layout.addRow("Nombre:*", self.txt_nombre)
        
        self.cmb_nivel = QComboBox()
        for nivel in NivelEquipo:
            self.cmb_nivel.addItem(nivel.value, nivel)
        form_layout.addRow("Nivel Jerarquía:*", self.cmb_nivel)
        
        self.cmb_almacen = SearchableComboBox()
        self.cargar_almacenes()
        form_layout.addRow("Ubicación Actual:", self.cmb_almacen)
        
        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(60)
        form_layout.addRow("Descripción:", self.txt_descripcion)
        
        # --- GRUPO TÉCNICO ---
        grp_tecnico = QGroupBox("Datos Técnicos")
        layout_tecnico = QFormLayout()
        
        self.txt_marca = UpperLineEdit()
        self.txt_modelo = UpperLineEdit()
        self.txt_serie = UpperLineEdit()
        
        layout_tecnico.addRow("Marca:", self.txt_marca)
        layout_tecnico.addRow("Modelo:", self.txt_modelo)
        layout_tecnico.addRow("Serie:", self.txt_serie)
        
        grp_tecnico.setLayout(layout_tecnico)
        layout.addWidget(grp_tecnico)
        
        # --- GRUPO CONTROL ---
        grp_control = QGroupBox("Control y Mantenimiento")
        layout_control = QVBoxLayout()
        
        # Calibración
        layout_calib = QHBoxLayout()
        self.chk_calibracion = QCheckBox("Requiere Calibración")
        self.date_vencimiento = QDateEdit()
        self.date_vencimiento.setCalendarPopup(True)
        self.date_vencimiento.setDate(QDate.currentDate().addYears(1))
        self.date_vencimiento.setEnabled(False)
        
        self.chk_calibracion.toggled.connect(self.date_vencimiento.setEnabled)
        
        layout_calib.addWidget(self.chk_calibracion)
        layout_calib.addWidget(QLabel("Vencimiento:"))
        layout_calib.addWidget(self.date_vencimiento)
        layout_control.addLayout(layout_calib)
        
        # Horómetro
        layout_horo = QHBoxLayout()
        self.chk_horometro = QCheckBox("Control por Horómetro")
        self.spn_horometro = QDoubleSpinBox()
        self.spn_horometro.setRange(0, 999999)
        self.spn_horometro.setSuffix(" Hrs")
        self.spn_horometro.setEnabled(False)
        
        self.chk_horometro.toggled.connect(self.spn_horometro.setEnabled)
        
        layout_horo.addWidget(self.chk_horometro)
        layout_horo.addWidget(QLabel("Actual:"))
        layout_horo.addWidget(self.spn_horometro)
        layout_control.addLayout(layout_horo)
        
        grp_control.setLayout(layout_control)
        layout.addWidget(grp_control)
        
        # --- GRUPO FINANCIERO ---
        grp_fin = QGroupBox("Datos Financieros")
        layout_fin = QHBoxLayout()
        
        layout_fin.addWidget(QLabel("Tarifa Diaria Ref.:"))
        self.spn_tarifa = QDoubleSpinBox()
        self.spn_tarifa.setRange(0, 99999)
        self.spn_tarifa.setPrefix("S/ ")
        layout_fin.addWidget(self.spn_tarifa)
        
        grp_fin.setLayout(layout_fin)
        layout.addWidget(grp_fin)
        
        layout.addLayout(form_layout)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.guardar)
        btn_guardar.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 8px 20px;")
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def cargar_almacenes(self):
        almacenes = self.session.query(Almacen).filter_by(activo=True).all()
        for alm in almacenes:
            self.cmb_almacen.addItem(alm.nombre, alm.id)

    def cargar_datos(self):
        self.txt_codigo.setText(self.equipo.codigo)
        self.txt_codigo.setEnabled(False) # No editar código
        self.txt_nombre.setText(self.equipo.nombre)
        self.txt_descripcion.setPlainText(self.equipo.descripcion or "")
        
        index = self.cmb_nivel.findData(self.equipo.nivel)
        if index >= 0: self.cmb_nivel.setCurrentIndex(index)
        
        index_alm = self.cmb_almacen.findData(self.equipo.almacen_id)
        if index_alm >= 0: self.cmb_almacen.setCurrentIndex(index_alm)
        
        self.txt_marca.setText(self.equipo.marca or "")
        self.txt_modelo.setText(self.equipo.modelo or "")
        self.txt_serie.setText(self.equipo.serie or "")
        
        self.chk_calibracion.setChecked(self.equipo.requiere_calibracion)
        if self.equipo.fecha_vencimiento_calibracion:
            self.date_vencimiento.setDate(self.equipo.fecha_vencimiento_calibracion)
            
        self.chk_horometro.setChecked(self.equipo.control_horometro)
        self.spn_horometro.setValue(self.equipo.horometro_actual)
        
        self.spn_tarifa.setValue(self.equipo.tarifa_diaria_referencial)

    def guardar(self):
        codigo = self.txt_codigo.text().strip()
        nombre = self.txt_nombre.text().strip()
        
        if not codigo or not nombre:
            QMessageBox.warning(self, "Error", "Código y Nombre son obligatorios.")
            return
            
        try:
            if not self.equipo:
                # Nuevo
                existe = self.session.query(Equipo).filter_by(codigo=codigo).first()
                if existe:
                    QMessageBox.warning(self, "Error", "El código ya existe.")
                    return
                
                self.equipo = Equipo(codigo=codigo)
                self.session.add(self.equipo)
            
            self.equipo.nombre = nombre
            self.equipo.descripcion = self.txt_descripcion.toPlainText()
            self.equipo.nivel = self.cmb_nivel.currentData()
            self.equipo.almacen_id = self.cmb_almacen.currentData()
            
            self.equipo.marca = self.txt_marca.text()
            self.equipo.modelo = self.txt_modelo.text()
            self.equipo.serie = self.txt_serie.text()
            
            self.equipo.requiere_calibracion = self.chk_calibracion.isChecked()
            if self.chk_calibracion.isChecked():
                self.equipo.fecha_vencimiento_calibracion = self.date_vencimiento.date().toPyDate()
            else:
                self.equipo.fecha_vencimiento_calibracion = None
                
            self.equipo.control_horometro = self.chk_horometro.isChecked()
            self.equipo.horometro_actual = self.spn_horometro.value()
            
            self.equipo.tarifa_diaria_referencial = self.spn_tarifa.value()
            
            self.session.commit()
            self.equipo_guardado.emit()
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}")

class EquiposWindow(BaseCRUDView):
    """Ventana de gestión de Equipos"""
    
    def __init__(self):
        super().__init__("Gestión de Equipos", Equipo, EquipoDialog)
        
    def setup_table_columns(self):
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "Código", "Nombre", "Nivel", "Estado", "Ubicación", "Venc. Calib.", "Acciones"
        ])
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
    def fill_row(self, row, item):
        self.tabla.setItem(row, 0, QTableWidgetItem(item.codigo))
        self.tabla.setItem(row, 1, QTableWidgetItem(item.nombre))
        self.tabla.setItem(row, 2, QTableWidgetItem(item.nivel.value))
        
        # Estado con color
        estado_item = QTableWidgetItem(item.estado.value)
        if item.estado == EstadoEquipo.DISPONIBLE:
            estado_item.setForeground(Qt.GlobalColor.darkGreen)
        elif item.estado == EstadoEquipo.MANTENIMIENTO:
            estado_item.setForeground(Qt.GlobalColor.darkRed)
        self.tabla.setItem(row, 3, estado_item)
        
        ubicacion = item.almacen.nombre if item.almacen else "Sin asignar"
        self.tabla.setItem(row, 4, QTableWidgetItem(ubicacion))
        
        venc = ""
        if item.requiere_calibracion and item.fecha_vencimiento_calibracion:
            venc = item.fecha_vencimiento_calibracion.strftime("%d/%m/%Y")
            # Semáforo
            dias = (item.fecha_vencimiento_calibracion - date.today()).days
            venc_item = QTableWidgetItem(venc)
            if dias < 0:
                venc_item.setBackground(Qt.GlobalColor.red)
                venc_item.setForeground(Qt.GlobalColor.white)
            elif dias < 30:
                venc_item.setBackground(Qt.GlobalColor.yellow)
                venc_item.setForeground(Qt.GlobalColor.black)
            self.tabla.setItem(row, 5, venc_item)
        else:
            self.tabla.setItem(row, 5, QTableWidgetItem("N/A"))

    def _open_dialog(self, item=None):
        dialog = EquipoDialog(self, equipo=item)
        dialog.equipo_guardado.connect(self.load_data)
        dialog.exec()
