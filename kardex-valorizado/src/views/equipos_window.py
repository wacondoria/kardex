from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidgetItem, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QMessageBox,
                             QComboBox, QCheckBox, QDateEdit, QDoubleSpinBox, QTextEdit, QFileDialog, QTabWidget, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSize
from PyQt6.QtGui import QFont, QPixmap
import sys
import os
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Equipo, Almacen, NivelEquipo, EstadoEquipo
from utils.widgets import SearchableComboBox, UpperLineEdit
from utils.file_manager import FileManager
from views.base_crud_view import BaseCRUDView

class EquipoDialog(QDialog):
    """Diálogo para crear/editar equipos"""
    
    equipo_guardado = pyqtSignal()

    def __init__(self, parent=None, equipo=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.equipo = equipo
        self.init_ui()
        
        if self.equipo:
            self.cargar_datos()
        
    def init_ui(self):
        self.setWindowTitle("Nuevo Equipo" if not self.equipo else "Editar Equipo")
        self.setFixedSize(700, 600)
        
        main_layout = QVBoxLayout()
        
        # --- TABS ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # === TAB 1: GENERAL ===
        tab_general = QWidget()
        layout_general = QVBoxLayout()
        
        # 1. Identificación
        grp_ident = QGroupBox("Identificación")
        form_ident = QFormLayout()
        self.txt_codigo = UpperLineEdit()
        self.txt_nombre = UpperLineEdit()
        form_ident.addRow("Código:*", self.txt_codigo)
        form_ident.addRow("Nombre:*", self.txt_nombre)
        grp_ident.setLayout(form_ident)
        layout_general.addWidget(grp_ident)
        
        # 2. Ubicación y Estado
        grp_ubic = QGroupBox("Ubicación y Estado")
        form_ubic = QFormLayout()
        
        self.cmb_nivel = QComboBox()
        for nivel in NivelEquipo:
            self.cmb_nivel.addItem(nivel.value, nivel)
            
        self.cmb_almacen = SearchableComboBox()
        self.cargar_almacenes()
        
        form_ubic.addRow("Nivel Jerarquía:*", self.cmb_nivel)
        form_ubic.addRow("Ubicación Actual:", self.cmb_almacen)
        grp_ubic.setLayout(form_ubic)
        layout_general.addWidget(grp_ubic)
        
        # 3. Descripción
        layout_general.addWidget(QLabel("Descripción:"))
        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(80)
        layout_general.addWidget(self.txt_descripcion)

        # 4. Foto Referencial
        grp_foto = QGroupBox("Foto Referencial")
        layout_foto = QHBoxLayout()
        
        self.lbl_foto = QLabel("Sin imagen")
        self.lbl_foto.setFixedSize(150, 150)
        self.lbl_foto.setScaledContents(True)
        self.lbl_foto.setStyleSheet("border: 1px dashed #ccc; background-color: #eee;")
        
        btn_cargar_foto = QPushButton("Cargar Multimedia")
        btn_cargar_foto.clicked.connect(self.cargar_foto)
        
        layout_foto.addWidget(self.lbl_foto)
        layout_foto.addWidget(btn_cargar_foto)
        layout_foto.addStretch()
        
        grp_foto.setLayout(layout_foto)
        layout_general.addWidget(grp_foto)
        
        tab_general.setLayout(layout_general)
        self.tabs.addTab(tab_general, "General")
        
        # === TAB 2: DETALLES TÉCNICOS ===
        tab_tecnico = QWidget()
        layout_tecnico = QVBoxLayout()
        
        # 1. Datos Técnicos
        grp_tec = QGroupBox("Datos Técnicos")
        form_tec = QFormLayout()
        self.txt_marca = UpperLineEdit()
        self.txt_modelo = UpperLineEdit()
        self.txt_serie = UpperLineEdit()
        form_tec.addRow("Marca:", self.txt_marca)
        form_tec.addRow("Modelo:", self.txt_modelo)
        form_tec.addRow("Serie:", self.txt_serie)
        grp_tec.setLayout(form_tec)
        layout_tecnico.addWidget(grp_tec)
        
        # 2. Control y Mantenimiento
        grp_mant = QGroupBox("Control y Mantenimiento")
        grid_mant = QGridLayout()
        
        self.chk_calibracion = QCheckBox("Requiere Calibración")
        self.chk_calibracion.toggled.connect(self.toggle_calibracion)
        self.date_vencimiento = QDateEdit(date.today())
        self.date_vencimiento.setCalendarPopup(True)
        self.date_vencimiento.setEnabled(False)
        
        grid_mant.addWidget(self.chk_calibracion, 0, 0)
        grid_mant.addWidget(QLabel("Vencimiento:"), 0, 1)
        grid_mant.addWidget(self.date_vencimiento, 0, 2)
        
        self.chk_horometro = QCheckBox("Control por Horómetro")
        self.chk_horometro.toggled.connect(self.toggle_horometro)
        self.spn_horometro = QDoubleSpinBox()
        self.spn_horometro.setRange(0, 999999)
        self.spn_horometro.setSuffix(" Hrs")
        self.spn_horometro.setEnabled(False)
        
        grid_mant.addWidget(self.chk_horometro, 1, 0)
        grid_mant.addWidget(QLabel("Actual:"), 1, 1)
        grid_mant.addWidget(self.spn_horometro, 1, 2)
        
        grp_mant.setLayout(grid_mant)
        layout_tecnico.addWidget(grp_mant)
        
        # 3. Datos Financieros
        grp_fin = QGroupBox("Datos Financieros")
        form_fin = QFormLayout()
        self.spn_tarifa = QDoubleSpinBox()
        self.spn_tarifa.setRange(0, 999999)
        self.spn_tarifa.setPrefix("S/ ")
        form_fin.addRow("Tarifa Diaria Ref.:", self.spn_tarifa)
        grp_fin.setLayout(form_fin)
        layout_tecnico.addWidget(grp_fin)
        
        layout_tecnico.addStretch()
        tab_tecnico.setLayout(layout_tecnico)
        self.tabs.addTab(tab_tecnico, "Detalles Técnicos")
        
        # --- FOOTER ---
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.guardar)
        btn_save.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        
        main_layout.addLayout(btn_box)
        self.setLayout(main_layout)

    def cargar_almacenes(self):
        almacenes = self.session.query(Almacen).filter_by(activo=True).all()
        for alm in almacenes:
            self.cmb_almacen.addItem(alm.nombre, alm.id)

    def toggle_calibracion(self, checked):
        self.date_vencimiento.setEnabled(checked)

    def toggle_horometro(self, checked):
        self.spn_horometro.setEnabled(checked)
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

        if self.equipo.foto_referencia:
            self.mostrar_multimedia(self.equipo.foto_referencia)
            self.ruta_foto_actual = self.equipo.foto_referencia

    def cargar_foto(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Seleccionar Multimedia", "", "Imágenes y Videos (*.png *.jpg *.jpeg *.mp4 *.avi *.mov)")
        if file_name:
            self.mostrar_multimedia(file_name)
            self.ruta_foto_actual = file_name

    def mostrar_multimedia(self, path):
        # Si es ruta relativa, obtener absoluta
        full_path = FileManager.get_full_path(path) if not os.path.isabs(path) else path
        
        if not full_path or not os.path.exists(full_path):
            self.lbl_foto.setText("No encontrado")
            return

        if FileManager.is_video(full_path):
            self.lbl_foto.setText("🎥 VIDEO")
            self.lbl_foto.setStyleSheet("border: 1px solid blue; color: blue; font-weight: bold; font-size: 16px;")
        else:
            pixmap = QPixmap(full_path)
            self.lbl_foto.setPixmap(pixmap)
            self.lbl_foto.setStyleSheet("border: 1px dashed #ccc; background-color: #eee;")

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
            
            # Guardar Foto/Video
            if self.ruta_foto_actual and self.ruta_foto_actual != self.equipo.foto_referencia:
                # Si es una ruta nueva (no la que ya tenía guardada)
                if os.path.isabs(self.ruta_foto_actual):
                    nueva_ruta = FileManager.save_file(self.ruta_foto_actual, "detalle_equipos")
                    self.equipo.foto_referencia = nueva_ruta
            
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
