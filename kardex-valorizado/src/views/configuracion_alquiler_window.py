"""
Ventana de Configuración para el Módulo de Alquileres
Archivo: src/views/configuracion_alquiler_window.py
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, 
                             QDoubleSpinBox, QMessageBox, QLabel, QGroupBox)
from PyQt6.QtCore import Qt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.database_model import obtener_session, Equipo, Proveedor
from views.importacion_alquiler_window import ImportacionAlquilerWindow
from utils.widgets import SearchableComboBox

class GestionDatosAlquilerWidget(QWidget):
    """Widget para gestionar tarifas y proveedores de equipos masivamente"""
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.cargar_datos()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Filtros (Opcional, por ahora simple)
        
        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["Código", "Equipo", "Proveedor", "Tarifa S/", "Tarifa $", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla)
        
        # Botón Guardar Todo (Opcional, o guardar fila por fila)
        # Por simplicidad, guardaremos fila por fila con un botón en la celda
        
        self.setLayout(layout)

    def cargar_datos(self):
        self.tabla.setRowCount(0)
        equipos = self.session.query(Equipo).filter_by(activo=True).all()
        proveedores = self.session.query(Proveedor).filter_by(activo=True).all()
        
        for eq in equipos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            
            self.tabla.setItem(row, 0, QTableWidgetItem(eq.codigo))
            self.tabla.setItem(row, 1, QTableWidgetItem(eq.nombre))
            
            # Proveedor (ComboBox)
            cmb_prov = SearchableComboBox()
            cmb_prov.addItem("Seleccionar...", None)
            for p in proveedores:
                cmb_prov.addItem(p.razon_social, p.id)
            
            if eq.proveedor_id:
                idx = cmb_prov.findData(eq.proveedor_id)
                if idx != -1: cmb_prov.setCurrentIndex(idx)
            
            self.tabla.setCellWidget(row, 2, cmb_prov)
            
            # Tarifa S/
            spn_soles = QDoubleSpinBox()
            spn_soles.setRange(0, 999999)
            spn_soles.setPrefix("S/ ")
            spn_soles.setValue(eq.tarifa_diaria_referencial or 0.0)
            self.tabla.setCellWidget(row, 3, spn_soles)
            
            # Tarifa $
            spn_dolares = QDoubleSpinBox()
            spn_dolares.setRange(0, 999999)
            spn_dolares.setPrefix("$ ")
            spn_dolares.setValue(eq.tarifa_diaria_dolares or 0.0)
            self.tabla.setCellWidget(row, 4, spn_dolares)
            
            # Botón Guardar
            btn_save = QPushButton("💾")
            btn_save.setToolTip("Guardar cambios de esta fila")
            btn_save.clicked.connect(lambda checked, r=row, e_id=eq.id: self.guardar_fila(r, e_id))
            self.tabla.setCellWidget(row, 5, btn_save)

    def guardar_fila(self, row, equipo_id):
        try:
            equipo = self.session.get(Equipo, equipo_id)
            if not equipo: return
            
            cmb_prov = self.tabla.cellWidget(row, 2)
            spn_soles = self.tabla.cellWidget(row, 3)
            spn_dolares = self.tabla.cellWidget(row, 4)
            
            equipo.proveedor_id = cmb_prov.currentData()
            equipo.tarifa_diaria_referencial = spn_soles.value()
            equipo.tarifa_diaria_dolares = spn_dolares.value()
            
            self.session.commit()
            QMessageBox.information(self, "Éxito", f"Datos actualizados para {equipo.codigo}")
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class ConfiguracionAlquilerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración del Módulo de Alquileres")
        self.setFixedSize(900, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        # Tab 1: Gestión de Datos (Tarifas/Proveedores)
        self.tab_datos = GestionDatosAlquilerWidget()
        self.tabs.addTab(self.tab_datos, "Gestión de Tarifas y Proveedores")
        
        # Tab 2: Importación
        self.tab_import = ImportacionAlquilerWindow()
        self.tabs.addTab(self.tab_import, "Importación Masiva")
        
        layout.addWidget(self.tabs)
        
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.setLayout(layout)
