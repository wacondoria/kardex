"""
Ventana de Importación para el Módulo de Alquileres
Archivo: src/views/importacion_alquiler_window.py
"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QGroupBox, QFormLayout
)
from PyQt6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.import_export_manager import ImportExportManager

class ImportacionAlquilerWindow(QWidget):
    """
    Ventana para importar datos masivos específicos del módulo de alquileres (Equipos con tarifas, etc).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = ImportExportManager(parent_widget=self)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Importación de Datos de Alquiler")
        self.setMinimumSize(500, 300)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Título
        header_layout = QHBoxLayout()
        title_label = QLabel("📥 Importación de Equipos (Datos Alquiler)")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Descripción
        desc_label = QLabel("Utilice esta herramienta para actualizar masivamente los datos de alquiler de los equipos (Tarifas, Proveedores).")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # Grupo de Acciones
        actions_group = QGroupBox("Acciones")
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(15)

        self.btn_generar_plantilla = QPushButton("📄 Generar Plantilla de Equipos")
        self.btn_generar_plantilla.setStyleSheet("padding: 10px; background-color: #1D6F42; color: white; font-weight: bold;")
        self.btn_generar_plantilla.clicked.connect(self.generar_plantilla)

        self.btn_importar_datos = QPushButton("⬆️ Importar Datos de Equipos")
        self.btn_importar_datos.setStyleSheet("padding: 10px; background-color: #107C41; color: white; font-weight: bold;")
        self.btn_importar_datos.clicked.connect(self.importar_datos)

        actions_layout.addWidget(self.btn_generar_plantilla)
        actions_layout.addWidget(self.btn_importar_datos)
        actions_group.setLayout(actions_layout)
        main_layout.addWidget(actions_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def generar_plantilla(self):
        # Por defecto usamos el módulo "Equipos" que ya maneja el ImportExportManager
        self.manager.generar_plantilla("Equipos")

    def importar_datos(self):
        self.manager.importar_datos("Equipos")
