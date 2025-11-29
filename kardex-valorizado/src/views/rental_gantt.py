from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                             QGraphicsTextItem, QComboBox, QPushButton, QDateEdit,
                             QGraphicsItem, QToolTip)
from PyQt6.QtCore import Qt, QDate, QRectF
from PyQt6.QtGui import QBrush, QColor, QPen, QFont
from models.database_model import obtener_session, Equipo, AlquilerDetalle, TipoEquipo, SubtipoEquipo, Alquiler, EstadoAlquiler
from sqlalchemy import text
from datetime import timedelta

class RentalGanttWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.current_date = QDate.currentDate()
        self.days_to_show = 30
        self.row_height = 40
        self.header_height = 50
        self.sidebar_width = 250
        self.day_width = 40
        
        self.init_ui()
        
        # DEBUG: Verify DB connection and schema
        try:
            print(f"DEBUG: RentalGantt DB URL: {self.session.bind.url}")
            result = self.session.execute(text("PRAGMA table_info(alquiler_detalles)")).fetchall()
            print(f"DEBUG: alquiler_detalles columns: {[r[1] for r in result]}")
        except Exception as e:
            print(f"DEBUG: Error checking schema: {e}")
            
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.btn_prev = QPushButton("< Anterior")
        self.btn_prev.clicked.connect(self.prev_period)
        
        self.date_selector = QDateEdit()
        self.date_selector.setDate(self.current_date)
        self.date_selector.setCalendarPopup(True)
        self.date_selector.dateChanged.connect(self.on_date_changed)
        
        self.btn_next = QPushButton("Siguiente >")
        self.btn_next.clicked.connect(self.next_period)
        
        self.cmb_view_mode = QComboBox()
        self.cmb_view_mode.addItems(["Mes (30 días)", "Semana (7 días)"])
        self.cmb_view_mode.currentIndexChanged.connect(self.change_view_mode)
        
        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.clicked.connect(self.load_data)
        
        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.date_selector)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addWidget(self.cmb_view_mode)
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(controls_layout)
        
        # Graphics View
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.view.setRenderHint(self.view.renderHints().Antialiasing)
        
        layout.addWidget(self.view)

    def change_view_mode(self, index):
        if index == 0: # Mes
            self.days_to_show = 30
            self.day_width = 40
        else: # Semana
            self.days_to_show = 7
            self.day_width = 100
        self.load_data()

    def prev_period(self):
        self.current_date = self.current_date.addDays(-self.days_to_show)
        self.date_selector.setDate(self.current_date)
        # load_data called by dateChanged

    def next_period(self):
        self.current_date = self.current_date.addDays(self.days_to_show)
        self.date_selector.setDate(self.current_date)

    def on_date_changed(self, date):
        self.current_date = date
        self.load_data()

    def load_data(self):
        self.scene.clear()
        
        # Fetch Equipos
        equipos = self.session.query(Equipo).filter(Equipo.activo == True).order_by(Equipo.tipo_equipo_id, Equipo.nombre).all()
        
        # Draw Header (Dates)
        self.draw_header()
        
        # Draw Rows (Equipos)
        y = self.header_height
        for equipo in equipos:
            self.draw_equipo_row(equipo, y)
            
            # Draw Rentals for this equipo
            self.draw_rentals(equipo, y)
            
            y += self.row_height
            
        # Set Scene Rect
        total_width = self.sidebar_width + (self.days_to_show * self.day_width)
        total_height = max(y, self.view.height())
        self.scene.setSceneRect(0, 0, total_width, total_height)

    def draw_header(self):
        # Sidebar Header
        rect = QGraphicsRectItem(0, 0, self.sidebar_width, self.header_height)
        rect.setBrush(QBrush(QColor("#2c3e50")))
        rect.setPen(QPen(Qt.GlobalColor.white))
        self.scene.addItem(rect)
        
        text = QGraphicsTextItem("Equipo / Modelo")
        text.setDefaultTextColor(Qt.GlobalColor.white)
        text.setPos(10, 15)
        text.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.scene.addItem(text)
        
        # Date Headers
        start_date = self.current_date
        for i in range(self.days_to_show):
            date = start_date.addDays(i)
            x = self.sidebar_width + (i * self.day_width)
            
            rect = QGraphicsRectItem(x, 0, self.day_width, self.header_height)
            rect.setBrush(QBrush(QColor("#34495e")))
            rect.setPen(QPen(QColor("#7f8c8d")))
            self.scene.addItem(rect)
            
            day_text = QGraphicsTextItem(f"{date.day}\n{date.toString('MMM')}")
            day_text.setDefaultTextColor(Qt.GlobalColor.white)
            day_text.setPos(x + 5, 5)
            self.scene.addItem(day_text)

    def draw_equipo_row(self, equipo, y):
        # Sidebar Item
        rect = QGraphicsRectItem(0, y, self.sidebar_width, self.row_height)
        rect.setBrush(QBrush(QColor("#ecf0f1")))
        rect.setPen(QPen(QColor("#bdc3c7")))
        self.scene.addItem(rect)
        
        name_text = QGraphicsTextItem(f"{equipo.codigo} - {equipo.nombre}")
        name_text.setPos(5, y + 10)
        self.scene.addItem(name_text)
        
        # Grid lines
        for i in range(self.days_to_show):
            x = self.sidebar_width + (i * self.day_width)
            grid_rect = QGraphicsRectItem(x, y, self.day_width, self.row_height)
            grid_rect.setPen(QPen(QColor("#ecf0f1"))) # Light grid
            self.scene.addItem(grid_rect)

    def draw_rentals(self, equipo, y):
        # Find rentals for this equipment overlapping current view
        start_view = self.current_date.toPyDate()
        end_view = self.current_date.addDays(self.days_to_show).toPyDate()
        
        detalles = self.session.query(AlquilerDetalle).join(Alquiler).filter(
            AlquilerDetalle.equipo_id == equipo.id,
            Alquiler.estado != EstadoAlquiler.ANULADO,
            Alquiler.fecha_inicio <= end_view,
            Alquiler.fecha_fin_estimada >= start_view
        ).all()
        
        for det in detalles:
            alquiler = det.alquiler
            
            # Calculate start and end pixels
            start_rent = alquiler.fecha_inicio
            end_rent = alquiler.fecha_fin_estimada
            
            # Clip to view
            effective_start = max(start_rent, start_view)
            effective_end = min(end_rent, end_view)
            
            days_from_start = (effective_start - start_view).days
            duration_days = (effective_end - effective_start).days + 1
            
            if duration_days <= 0:
                continue
                
            x = self.sidebar_width + (days_from_start * self.day_width)
            width = duration_days * self.day_width
            
            # Bar Color based on status
            color = QColor("#2ecc71") # Green (Active)
            if alquiler.estado == EstadoAlquiler.COTIZACION:
                color = QColor("#f1c40f") # Yellow
            elif alquiler.estado == EstadoAlquiler.FINALIZADO:
                color = QColor("#95a5a6") # Grey
                
            bar = QGraphicsRectItem(x, y + 5, width, self.row_height - 10)
            bar.setBrush(QBrush(color))
            bar.setPen(QPen(Qt.GlobalColor.black))
            bar.setToolTip(f"Cliente: {alquiler.cliente.razon_social}\nProyecto: {alquiler.proyecto.nombre if alquiler.proyecto else 'N/A'}\nDesde: {start_rent}\nHasta: {end_rent}")
            
            self.scene.addItem(bar)
            
            # Text on bar
            if width > 50:
                label = QGraphicsTextItem(alquiler.cliente.razon_social[:15], bar)
                label.setPos(x + 2, y + 10)
                label.setDefaultTextColor(Qt.GlobalColor.black)

    def closeEvent(self, event):
        self.session.close()
        super().closeEvent(event)
