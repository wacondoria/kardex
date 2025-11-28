from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QPushButton, QHBoxLayout)
from PyQt6.QtCore import Qt
from models.database_model import obtener_session, Equipo, AlquilerDetalle, Alquiler

class EquipoHistoryDialog(QDialog):
    def __init__(self, parent=None, equipo_id=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.equipo_id = equipo_id
        self.init_ui()
        self.load_history()

    def init_ui(self):
        self.setWindowTitle("Historial de Ubicaciones y Uso")
        self.resize(900, 500)
        
        layout = QVBoxLayout()
        
        # Header info
        self.lbl_info = QLabel("Cargando...")
        self.lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.lbl_info)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Fecha Inicio", "Fecha Fin", "Cliente", "Obra", 
            "H. Salida", "H. Retorno", "H. Uso"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def load_history(self):
        if not self.equipo_id:
            return
            
        equipo = self.session.query(Equipo).get(self.equipo_id)
        if not equipo:
            self.lbl_info.setText("Equipo no encontrado")
            return
            
        self.lbl_info.setText(f"Historial de: {equipo.codigo} - {equipo.nombre}")
        
        # Query details linked to this equipment
        detalles = self.session.query(AlquilerDetalle).join(Alquiler).filter(
            AlquilerDetalle.equipo_id == self.equipo_id
        ).order_by(Alquiler.fecha_inicio.desc()).all()
        
        self.table.setRowCount(0)
        for det in detalles:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Fechas
            fecha_inicio = det.fecha_salida.strftime("%d/%m/%Y") if det.fecha_salida else det.alquiler.fecha_inicio.strftime("%d/%m/%Y")
            
            fecha_fin = "-"
            if det.fecha_retorno:
                fecha_fin = det.fecha_retorno.strftime("%d/%m/%Y")
            elif det.alquiler.fecha_fin_estimada:
                fecha_fin = f"(Est.) {det.alquiler.fecha_fin_estimada.strftime('%d/%m/%Y')}"
                
            self.table.setItem(row, 0, QTableWidgetItem(fecha_inicio))
            self.table.setItem(row, 1, QTableWidgetItem(fecha_fin))
            self.table.setItem(row, 2, QTableWidgetItem(det.alquiler.cliente.razon_social_o_nombre))
            self.table.setItem(row, 3, QTableWidgetItem(det.alquiler.ubicacion_obra or "-"))
            
            self.table.setItem(row, 4, QTableWidgetItem(str(det.horometro_salida)))
            self.table.setItem(row, 5, QTableWidgetItem(str(det.horometro_retorno)))
            self.table.setItem(row, 6, QTableWidgetItem(str(det.horas_uso)))

    def closeEvent(self, event):
        self.session.close()
        super().closeEvent(event)
