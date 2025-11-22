from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap

class ModuleSelector(QWidget):
    """
    Ventana de selección de módulo (Kardex vs Alquileres).
    Se muestra después del login exitoso.
    """
    
    module_selected = pyqtSignal(str) # Emite 'kardex' o 'rental'

    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Selección de Módulo - Sistema Integrado")
        self.setFixedSize(800, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f6fa;
            }
            QPushButton {
                background-color: white;
                border: 2px solid #dcdde1;
                border-radius: 15px;
                padding: 20px;
                text-align: center;
            }
            QPushButton:hover {
                border-color: #3498db;
                background-color: #ecf0f1;
            }
            QLabel#Title {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
            QLabel#Subtitle {
                font-size: 16px;
                color: #7f8c8d;
            }
            QLabel#ModuleTitle {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-top: 10px;
            }
            QLabel#ModuleDesc {
                font-size: 14px;
                color: #7f8c8d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)

        # Header
        header_layout = QVBoxLayout()
        title = QLabel(f"Bienvenido, {self.user_info.get('nombre_completo', 'Usuario')}")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Seleccione el módulo al que desea ingresar")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)

        # Buttons Container
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(40)

        # --- BOTÓN KARDEX ---
        btn_kardex = QPushButton()
        btn_kardex.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_kardex.setCheckable(False)
        btn_kardex.clicked.connect(lambda: self.select_module('kardex'))
        
        kardex_layout = QVBoxLayout(btn_kardex)
        kardex_icon = QLabel("📊") # Placeholder for icon
        kardex_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kardex_icon.setStyleSheet("font-size: 60px;")
        
        kardex_title = QLabel("Kardex Valorizado")
        kardex_title.setObjectName("ModuleTitle")
        kardex_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        kardex_desc = QLabel("Control de inventarios,\ncompras, ventas y costos.")
        kardex_desc.setObjectName("ModuleDesc")
        kardex_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        kardex_layout.addWidget(kardex_icon)
        kardex_layout.addWidget(kardex_title)
        kardex_layout.addWidget(kardex_desc)
        
        # --- BOTÓN ALQUILERES ---
        btn_rental = QPushButton()
        btn_rental.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rental.clicked.connect(lambda: self.select_module('rental'))
        
        rental_layout = QVBoxLayout(btn_rental)
        rental_icon = QLabel("🚜") # Placeholder for icon
        rental_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rental_icon.setStyleSheet("font-size: 60px;")
        
        rental_title = QLabel("Gestión de Activos")
        rental_title.setObjectName("ModuleTitle")
        rental_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        rental_desc = QLabel("Alquiler de equipos,\ncontrol de calibración y kits.")
        rental_desc.setObjectName("ModuleDesc")
        rental_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        rental_layout.addWidget(rental_icon)
        rental_layout.addWidget(rental_title)
        rental_layout.addWidget(rental_desc)

        buttons_layout.addWidget(btn_kardex)
        buttons_layout.addWidget(btn_rental)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()

    def select_module(self, module_name):
        self.module_selected.emit(module_name)
        self.close()
