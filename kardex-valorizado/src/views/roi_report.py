from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit)
from PyQt6.QtCore import Qt
from models.database_model import obtener_session, Equipo, AlquilerDetalle, OrdenMantenimiento
from datetime import date

class ROIReportWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.calculate_roi()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📈 Reporte de Rentabilidad (ROI)")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.calculate_roi)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_refresh)
        layout.addLayout(header)
        
        # Summary Cards (Optional, maybe later)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Equipo", "Costo Adquisición", "Ingresos Alquiler", 
            "Costos Mant.", "Utilidad Neta", "ROI %", "Estado"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.setLayout(layout)

    def calculate_roi(self):
        self.table.setRowCount(0)
        equipos = self.session.query(Equipo).filter(Equipo.activo == True).all()
        
        for row, eq in enumerate(equipos):
            # 1. Acquisition Cost
            costo_adq = eq.valor_adquisicion or 0.0
            
            # 2. Income (Rental)
            # Sum of all finalized or active rental details
            ingresos = 0.0
            for det in eq.detalles_alquiler:
                ingresos += (det.total or 0.0)
                
            # 3. Maintenance Costs
            costos_mant = 0.0
            for mant in eq.mantenimientos:
                costos_mant += (mant.costo_total or 0.0)
                
            # 4. Net Profit
            # Profit = Income - Maintenance - Acquisition
            # Note: Usually ROI considers profit over investment.
            # Net Profit (Lifetime) = Income - Maintenance - Acquisition
            utilidad = ingresos - costos_mant - costo_adq
            
            # 5. ROI %
            # ROI = (Net Profit / Investment) * 100
            roi = 0.0
            if costo_adq > 0:
                roi = (utilidad / costo_adq) * 100
            elif costo_adq == 0 and utilidad > 0:
                roi = 100.0 # Infinite return technically
            
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"{eq.codigo} - {eq.nombre}"))
            self.table.setItem(row, 1, QTableWidgetItem(f"S/ {costo_adq:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"S/ {ingresos:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"S/ {costos_mant:.2f}"))
            
            item_util = QTableWidgetItem(f"S/ {utilidad:.2f}")
            if utilidad >= 0:
                item_util.setForeground(Qt.GlobalColor.green)
            else:
                item_util.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 4, item_util)
            
            item_roi = QTableWidgetItem(f"{roi:.1f}%")
            if roi > 0:
                item_roi.setForeground(Qt.GlobalColor.green)
            else:
                item_roi.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 5, item_roi)
            
            self.table.setItem(row, 6, QTableWidgetItem(eq.estado.value))
