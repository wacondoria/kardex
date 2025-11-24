from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QSplitter, QListWidget, QGroupBox,
                             QFormLayout, QSpinBox, QCheckBox, QMessageBox, QDialog, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, TipoEquipo, KitComponente, Equipo, NivelEquipo
from utils.widgets import UpperLineEdit, SearchableComboBox

class KitDialog(QDialog):
    """Diálogo para crear/editar un Kit (Cabecera)"""
    kit_guardado = pyqtSignal()

    def __init__(self, parent=None, kit=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.kit = kit
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Nuevo Kit" if not self.kit else "Editar Kit")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: KIT TERMOFUSIÓN 315")
        form.addRow("Nombre Kit:*", self.txt_nombre)
        
        self.txt_desc = QLineEdit()
        form.addRow("Descripción:", self.txt_desc)
        
        layout.addLayout(form)
        
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.guardar)
        layout.addWidget(btn_save)
        
        self.setLayout(layout)
        
        if self.kit:
            self.txt_nombre.setText(self.kit.nombre)
            self.txt_desc.setText(self.kit.descripcion or "")

    def guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre: return
        
        try:
            if not self.kit:
                self.kit = TipoEquipo(nombre=nombre, descripcion=self.txt_desc.text())
                self.session.add(self.kit)
            else:
                self.kit.nombre = nombre
                self.kit.descripcion = self.txt_desc.text()
                
            self.session.commit()
            self.kit_guardado.emit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class ComponenteDialog(QDialog):
    """Diálogo para agregar componente al Kit"""
    componente_guardado = pyqtSignal()

    def __init__(self, kit_id, parent=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.kit_id = kit_id
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Agregar Componente")
        self.setFixedSize(500, 300)
        
        layout = QFormLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: Unidad Hidráulica")
        layout.addRow("Nombre Componente:*", self.txt_nombre)
        
        self.cmb_nivel = QComboBox()
        self.cmb_nivel.addItem("Cualquiera / No Aplica", None)
        for nivel in NivelEquipo:
            self.cmb_nivel.addItem(nivel.value, nivel)
        layout.addRow("Nivel Requerido:", self.cmb_nivel)
        
        self.cmb_equipo = SearchableComboBox()
        self.cmb_equipo.addItem("Ninguno (Genérico)", None)
        self.cargar_equipos()
        layout.addRow("Equipo Sugerido:", self.cmb_equipo)
        
        self.spn_cantidad = QSpinBox()
        self.spn_cantidad.setRange(1, 100)
        layout.addRow("Cantidad:", self.spn_cantidad)
        
        self.chk_opcional = QCheckBox("Es Opcional")
        layout.addRow("", self.chk_opcional)
        
        btn_save = QPushButton("Agregar")
        btn_save.clicked.connect(self.guardar)
        layout.addRow(btn_save)
        
        self.setLayout(layout)

    def cargar_equipos(self):
        equipos = self.session.query(Equipo).filter_by(activo=True).all()
        for eq in equipos:
            self.cmb_equipo.addItem(f"{eq.codigo} - {eq.nombre}", eq.id)

    def guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre: return
        
        try:
            comp = KitComponente(
                tipo_equipo_id=self.kit_id,
                nombre_componente=nombre,
                nivel_requerido=self.cmb_nivel.currentData(),
                equipo_default_id=self.cmb_equipo.currentData(),
                cantidad=self.spn_cantidad.value(),
                es_opcional=self.chk_opcional.isChecked()
            )
            self.session.add(comp)
            self.session.commit()
            self.componente_guardado.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

class KitsWindow(QWidget):
    """Ventana de gestión de Kits"""
    
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.cargar_kits()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📦 Gestión de Kits (Plantillas)")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        
        btn_new_kit = QPushButton("+ Nuevo Kit")
        btn_new_kit.clicked.connect(self.nuevo_kit)
        header.addWidget(btn_new_kit)
        
        layout.addLayout(header)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Lista de Kits (Izquierda)
        self.list_kits = QListWidget()
        self.list_kits.itemClicked.connect(self.cargar_componentes)
        splitter.addWidget(self.list_kits)
        
        # Detalles del Kit (Derecha)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.lbl_kit_selected = QLabel("Seleccione un Kit")
        self.lbl_kit_selected.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(self.lbl_kit_selected)
        
        # Tabla Componentes
        self.table_comp = QTableWidget()
        self.table_comp.setColumnCount(5)
        self.table_comp.setHorizontalHeaderLabels(["Componente", "Nivel", "Equipo Sugerido", "Cant.", "Opcional"])
        right_layout.addWidget(self.table_comp)
        
        btn_add_comp = QPushButton("+ Agregar Componente")
        btn_add_comp.clicked.connect(self.agregar_componente)
        right_layout.addWidget(btn_add_comp)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)

    def cargar_kits(self):
        self.list_kits.clear()
        kits = self.session.query(TipoEquipo).filter_by(activo=True).all()
        for kit in kits:
            item = QTableWidgetItem(kit.nombre) # QListWidget usa QListWidgetItem, pero bueno
            self.list_kits.addItem(f"{kit.id} - {kit.nombre}")

    def nuevo_kit(self):
        dialog = KitDialog(self)
        dialog.kit_guardado.connect(self.cargar_kits)
        dialog.exec()

    def cargar_componentes(self, item):
        text = item.text()
        kit_id = int(text.split(' - ')[0])
        self.current_kit_id = kit_id
        
        kit = self.session.query(TipoEquipo).get(kit_id)
        self.lbl_kit_selected.setText(f"Componentes de: {kit.nombre}")
        
        self.table_comp.setRowCount(0)
        for comp in kit.componentes:
            row = self.table_comp.rowCount()
            self.table_comp.insertRow(row)
            
            self.table_comp.setItem(row, 0, QTableWidgetItem(comp.nombre_componente))
            self.table_comp.setItem(row, 1, QTableWidgetItem(comp.nivel_requerido.value if comp.nivel_requerido else "-"))
            
            eq_nombre = comp.equipo_default.nombre if comp.equipo_default else "-"
            self.table_comp.setItem(row, 2, QTableWidgetItem(eq_nombre))
            
            self.table_comp.setItem(row, 3, QTableWidgetItem(str(comp.cantidad)))
            self.table_comp.setItem(row, 4, QTableWidgetItem("Sí" if comp.es_opcional else "No"))

    def agregar_componente(self):
        if not hasattr(self, 'current_kit_id'):
            QMessageBox.warning(self, "Aviso", "Seleccione un kit primero")
            return
            
        dialog = ComponenteDialog(self.current_kit_id, self)
        dialog.componente_guardado.connect(lambda: self.cargar_componentes(self.list_kits.currentItem()))
        dialog.exec()
