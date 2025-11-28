from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QCalendarWidget, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QSplitter)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush, QTextCharFormat
from models.database_model import obtener_session, Equipo

class MaintenanceCalendar(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.fechas_eventos = {} # {QDate: [lista_equipos]}
        self.init_ui()
        self.cargar_datos()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📅 Calendario de Mantenimiento y Calibración")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a73e8;")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Calendario
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.mostrar_eventos_dia)
        self.calendar.selectionChanged.connect(self.mostrar_eventos_dia)
        splitter.addWidget(self.calendar)

        # Lista de Eventos
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Código", "Equipo", "Evento"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.tabla)

        splitter.setSizes([500, 500])
        layout.addWidget(splitter)
        self.setLayout(layout)

    def cargar_datos(self):
        equipos = self.session.query(Equipo).filter(Equipo.activo == True).all()
        self.fechas_eventos = {}

        fmt_calibracion = QTextCharFormat()
        fmt_calibracion.setBackground(QBrush(QColor("#fce8b2"))) # Amarillo claro
        fmt_calibracion.setFontWeight(75) # Bold

        for eq in equipos:
            if eq.fecha_vencimiento_calibracion:
                fecha = QDate(eq.fecha_vencimiento_calibracion.year, 
                              eq.fecha_vencimiento_calibracion.month, 
                              eq.fecha_vencimiento_calibracion.day)
                
                if fecha not in self.fechas_eventos:
                    self.fechas_eventos[fecha] = []
                
                self.fechas_eventos[fecha].append({
                    "codigo": eq.codigo,
                    "nombre": eq.nombre,
                    "tipo": "Vencimiento Calibración"
                })
                
                # Marcar en calendario
                self.calendar.setDateTextFormat(fecha, fmt_calibracion)

        # Refrescar vista del día actual
        self.mostrar_eventos_dia()

    def mostrar_eventos_dia(self):
        fecha = self.calendar.selectedDate()
        eventos = self.fechas_eventos.get(fecha, [])
        
        self.tabla.setRowCount(len(eventos))
        for row, evt in enumerate(eventos):
            self.tabla.setItem(row, 0, QTableWidgetItem(evt['codigo']))
            self.tabla.setItem(row, 1, QTableWidgetItem(evt['nombre']))
            self.tabla.setItem(row, 2, QTableWidgetItem(evt['tipo']))
