"""
Ventana de Configuración para el Módulo de Alquileres
Archivo: src/views/configuracion_alquiler_window.py
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton)
from PyQt6.QtCore import Qt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from views.importacion_alquiler_window import ImportacionAlquilerWindow

class ConfiguracionAlquilerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración del Módulo de Alquileres")
        self.setFixedSize(900, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Importación Masiva (Única opción por ahora)
        self.import_widget = ImportacionAlquilerWindow()
        layout.addWidget(self.import_widget)
        
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.setLayout(layout)
