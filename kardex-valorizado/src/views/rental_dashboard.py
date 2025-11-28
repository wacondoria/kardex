from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from models.database_model import obtener_session, Equipo, Operador, Alquiler, EstadoAlquiler, EstadoEquipo
from datetime import date, timedelta

class AlertCard(QFrame):
    def __init__(self, title, message, urgency="normal"):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_msg)
        
        # Style based on urgency
        if urgency == "critical":
            self.setStyleSheet("AlertCard { background-color: #fadbd8; border: 1px solid #e74c3c; border-radius: 5px; } QLabel { color: #c0392b; }")
        elif urgency == "warning":
            self.setStyleSheet("AlertCard { background-color: #fcf3cf; border: 1px solid #f1c40f; border-radius: 5px; } QLabel { color: #d35400; }")
        else:
            self.setStyleSheet("AlertCard { background-color: #d1f2eb; border: 1px solid #2ecc71; border-radius: 5px; } QLabel { color: #27ae60; }")

class RentalDashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.load_alerts()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Dashboard de Alertas y Vencimientos")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        header.addStretch()
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.load_alerts)
        header.addWidget(btn_refresh)
        
        layout.addLayout(header)
        
        # Content Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.content_widget)
        
        layout.addWidget(scroll)

    def load_alerts(self):
        # Clear existing
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
            
        row = 0
        col = 0
        max_cols = 3
        
        today = date.today()
        warning_threshold = timedelta(days=30)
        critical_threshold = timedelta(days=7)
        
        # 1. Calibration Alerts
        equipos = self.session.query(Equipo).filter(
            Equipo.activo == True,
            Equipo.requiere_calibracion == True,
            Equipo.fecha_vencimiento_calibracion != None
        ).all()
        
        for eq in equipos:
            days = (eq.fecha_vencimiento_calibracion - today).days
            urgency = None
            msg = ""
            
            if days < 0:
                urgency = "critical"
                msg = f"VENCIDO hace {abs(days)} días ({eq.fecha_vencimiento_calibracion})"
            elif days <= 7:
                urgency = "critical"
                msg = f"Vence en {days} días ({eq.fecha_vencimiento_calibracion})"
            elif days <= 30:
                urgency = "warning"
                msg = f"Vence en {days} días ({eq.fecha_vencimiento_calibracion})"
                
            if urgency:
                card = AlertCard(f"🔧 Calibración: {eq.codigo}", msg, urgency)
                self.add_card(card, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        # 2. Operator License Alerts
        operadores = self.session.query(Operador).filter(
            Operador.activo == True,
            Operador.fecha_vencimiento_licencia != None
        ).all()
        
        for op in operadores:
            days = (op.fecha_vencimiento_licencia - today).days
            urgency = None
            msg = ""
            
            if days < 0:
                urgency = "critical"
                msg = f"Licencia VENCIDA hace {abs(days)} días"
            elif days <= 7:
                urgency = "critical"
                msg = f"Licencia vence en {days} días"
            elif days <= 30:
                urgency = "warning"
                msg = f"Licencia vence en {days} días"
                
            if urgency:
                card = AlertCard(f"👷 Operador: {op.nombre}", msg, urgency)
                self.add_card(card, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        # 3. Rental Return Alerts
        alquileres = self.session.query(Alquiler).filter(
            Alquiler.estado == EstadoAlquiler.ACTIVO,
            Alquiler.fecha_fin_estimada != None
        ).all()
        
        for alq in alquileres:
            days = (alq.fecha_fin_estimada - today).days
            urgency = None
            msg = ""
            
            if days < 0:
                urgency = "critical"
                msg = f"Retorno ATRASADO por {abs(days)} días"
            elif days <= 3:
                urgency = "warning"
                msg = f"Retorno programado en {days} días"
                
            if urgency:
                cliente_name = alq.cliente.razon_social_o_nombre[:20] + "..." if len(alq.cliente.razon_social_o_nombre) > 20 else alq.cliente.razon_social_o_nombre
                card = AlertCard(f"📅 Alquiler #{alq.id}: {cliente_name}", msg, urgency)
                self.add_card(card, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        if self.grid_layout.count() == 0:
            lbl = QLabel("✅ No hay alertas pendientes")
            lbl.setStyleSheet("font-size: 16px; color: #7f8c8d; margin: 20px;")
            self.grid_layout.addWidget(lbl, 0, 0)

    def add_card(self, card, row, col):
        self.grid_layout.addWidget(card, row, col)

    def closeEvent(self, event):
        self.session.close()
        super().closeEvent(event)
