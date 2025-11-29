from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QWidget, QTabWidget, QToolBar, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from utils.app_context import app_context
from views.equipos_window import EquiposWindow
from views.kits_window import KitsWindow
from views.alquileres_window import AlquileresWindow
from views.configuracion_alquiler_window import ConfiguracionAlquilerDialog
from views.checklist_window import ChecklistManagerWidget
from views.operadores_window import OperadoresWindow
from views.rental_dashboard import RentalDashboardWidget
from views.proyectos_window import ProyectosWindow
from views.rental_gantt import RentalGanttWidget
from views.maintenance_window import MaintenanceWindow
from views.roi_report import ROIReportWindow

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
        
        btn_proyectos = QPushButton("🏗️ Proyectos")
        btn_proyectos.clicked.connect(self.abrir_proyectos)
        toolbar.addWidget(btn_proyectos)

        toolbar.addSeparator()
        
        btn_alquileres = QPushButton("📄 Alquileres")
        btn_alquileres.clicked.connect(self.abrir_alquileres)
        toolbar.addWidget(btn_alquileres)

        toolbar.addSeparator()

        btn_config = QPushButton("⚙️ Configuración")
        btn_config.clicked.connect(self.abrir_configuracion)
        toolbar.addWidget(btn_config)
        
        btn_operadores = QPushButton("👷 Operadores")
        btn_operadores.clicked.connect(self.abrir_operadores)
        btn_operadores = QPushButton("👷 Operadores")
        btn_operadores.clicked.connect(self.abrir_operadores)
        toolbar.addWidget(btn_operadores)
        
        btn_mant = QPushButton("🔧 Mantenimiento")
        btn_mant.clicked.connect(self.abrir_mantenimiento)
        toolbar.addWidget(btn_mant)
        
        btn_roi = QPushButton("📈 ROI")
        btn_roi.clicked.connect(self.abrir_roi)
        toolbar.addWidget(btn_roi)
        
        toolbar.addSeparator()
        
        btn_volver = QPushButton("🔙 Volver al Menú Principal")
        btn_volver.clicked.connect(self.return_to_menu.emit)
        toolbar.addWidget(btn_volver)

        # Central Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.cerrar_pestana)
        self.setCentralWidget(self.tab_widget)
        
        # Dashboard
        self.dashboard_widget = RentalDashboardWidget()
        self.tab_widget.addTab(self.dashboard_widget, "📊 Dashboard")
        
        # Gantt Chart (Disponibilidad)
        self.gantt_widget = RentalGanttWidget()
        self.tab_widget.addTab(self.gantt_widget, "📅 Disponibilidad")

        # Checklists
        self.checklist_widget = ChecklistManagerWidget()
        self.tab_widget.addTab(self.checklist_widget, "📋 Checklists")

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

    def abrir_proyectos(self):
        nombre_pestana = "Gestión de Proyectos"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return
        
        proyectos_widget = ProyectosWindow()
        self.tab_widget.addTab(proyectos_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(proyectos_widget)

    def abrir_configuracion(self):
        dialog = ConfiguracionAlquilerDialog(self)
        dialog.exec()

    def abrir_operadores(self):
        nombre_pestana = "Gestión de Operadores"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return
        
        operadores_widget = OperadoresWindow()
        self.tab_widget.addTab(operadores_widget, nombre_pestana)
        self.tab_widget.addTab(operadores_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(operadores_widget)

    def abrir_mantenimiento(self):
        nombre_pestana = "Gestión de Mantenimiento"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return
        
        mant_widget = MaintenanceWindow()
        self.tab_widget.addTab(mant_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(mant_widget)

    def abrir_roi(self):
        nombre_pestana = "Reporte ROI"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return
        
        roi_widget = ROIReportWindow()
        self.tab_widget.addTab(roi_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(roi_widget)
