from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QWidget, QTabWidget, QToolBar, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from utils.app_context import app_context
from views.equipos_window import EquiposWindow
from views.kits_window import KitsWindow
from views.alquileres_window import AlquileresWindow
from views.configuracion_alquiler_window import ConfiguracionAlquilerDialog

class RentalMainWindow(QMainWindow):
    """
    Ventana principal del módulo de Control de Alquileres.
    """
    return_to_menu = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.user_info = app_context.get_user_info()
        self.selected_year = app_context.get_selected_year()
        
        # Guardar referencia en el contexto (opcional, si queremos separar contextos)
        # app_context.set_rental_window(self) 

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Gestión de Activos y Alquileres - {self.user_info['nombre_completo']} | Año: {self.selected_year}")
        self.showMaximized()
        
        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        btn_equipos = QPushButton("🚜 Equipos")
        btn_equipos.clicked.connect(self.abrir_equipos)
        toolbar.addWidget(btn_equipos)
        
        btn_kits = QPushButton("📦 Kits")
        btn_kits.clicked.connect(self.abrir_kits)
        toolbar.addWidget(btn_kits)
        
        toolbar.addSeparator()
        
        btn_alquileres = QPushButton("📄 Alquileres")
        btn_alquileres.clicked.connect(self.abrir_alquileres)
        toolbar.addWidget(btn_alquileres)

        toolbar.addSeparator()

        btn_config = QPushButton("⚙️ Configuración")
        btn_config.clicked.connect(self.abrir_configuracion)
        toolbar.addWidget(btn_config)
        
        toolbar.addSeparator()
        
        btn_volver = QPushButton("🔙 Volver al Menú Principal")
        btn_volver.clicked.connect(self.return_to_menu.emit)
        toolbar.addWidget(btn_volver)

        # Central Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.cerrar_pestana)
        self.setCentralWidget(self.tab_widget)
        
        # Dashboard Placeholder
        dashboard = QLabel("Dashboard de Alquileres (En Construcción)")
        dashboard.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dashboard.setStyleSheet("font-size: 20px; color: #7f8c8d;")
        self.tab_widget.addTab(dashboard, "📊 Dashboard")

    def cerrar_pestana(self, index):
        widget = self.tab_widget.widget(index)
        if widget:
            widget.deleteLater()
        self.tab_widget.removeTab(index)

    def abrir_equipos(self):
        nombre_pestana = "Gestión de Equipos"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return
        
        equipos_widget = EquiposWindow()
        self.tab_widget.addTab(equipos_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(equipos_widget)

    def abrir_kits(self):
        nombre_pestana = "Gestión de Kits"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return
        
        kits_widget = KitsWindow()
        self.tab_widget.addTab(kits_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(kits_widget)

    def abrir_alquileres(self):
        nombre_pestana = "Gestión de Alquileres"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return
        
        alquileres_widget = AlquileresWindow()
        self.tab_widget.addTab(alquileres_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(alquileres_widget)

    def abrir_configuracion(self):
        dialog = ConfiguracionAlquilerDialog(self)
        dialog.exec()
