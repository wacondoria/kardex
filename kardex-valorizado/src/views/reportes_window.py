from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QDateEdit, QGroupBox, 
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import QDate, Qt
from datetime import date
from services.report_service import ReportService
from models.database_model import obtener_session
import os

class ReportesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.report_service = ReportService(self.session)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📊 Reportes Avanzados")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a73e8;")
        layout.addWidget(title)

        # --- Reporte de Inventario ---
        grp_inv = QGroupBox("Inventario Valorizado")
        layout_inv = QHBoxLayout()
        
        btn_inv_pdf = QPushButton("Exportar PDF")
        btn_inv_pdf.clicked.connect(lambda: self.generar_inventario('pdf'))
        
        btn_inv_excel = QPushButton("Exportar Excel")
        btn_inv_excel.clicked.connect(lambda: self.generar_inventario('excel'))

        layout_inv.addWidget(QLabel("Generar reporte de stock actual y valorizado:"))
        layout_inv.addStretch()
        layout_inv.addWidget(btn_inv_pdf)
        layout_inv.addWidget(btn_inv_excel)
        grp_inv.setLayout(layout_inv)
        layout.addWidget(grp_inv)

        # --- Reporte de Ventas ---
        grp_ventas = QGroupBox("Reporte de Ventas")
        layout_ventas = QHBoxLayout()

        self.date_inicio = QDateEdit()
        self.date_inicio.setCalendarPopup(True)
        self.date_inicio.setDate(QDate.currentDate().addDays(-30))

        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDate(QDate.currentDate())

        btn_ventas_pdf = QPushButton("Exportar PDF")
        btn_ventas_pdf.clicked.connect(lambda: self.generar_ventas('pdf'))

        btn_ventas_excel = QPushButton("Exportar Excel")
        btn_ventas_excel.clicked.connect(lambda: self.generar_ventas('excel'))

        layout_ventas.addWidget(QLabel("Desde:"))
        layout_ventas.addWidget(self.date_inicio)
        layout_ventas.addWidget(QLabel("Hasta:"))
        layout_ventas.addWidget(self.date_fin)
        layout_ventas.addStretch()
        layout_ventas.addWidget(btn_ventas_pdf)
        layout_ventas.addWidget(btn_ventas_excel)
        grp_ventas.setLayout(layout_ventas)
        layout.addWidget(grp_ventas)

        layout.addStretch()
        self.setLayout(layout)

    def generar_inventario(self, formato):
        try:
            path = self.report_service.generar_reporte_inventario(formato)
            self._mostrar_exito(path)
        except Exception as e:
            self._mostrar_error(str(e))

    def generar_ventas(self, formato):
        try:
            f_inicio = self.date_inicio.date().toPyDate()
            f_fin = self.date_fin.date().toPyDate()
            path = self.report_service.generar_reporte_ventas(f_inicio, f_fin, formato)
            self._mostrar_exito(path)
        except Exception as e:
            self._mostrar_error(str(e))

    def _mostrar_exito(self, path):
        msg = QMessageBox(self)
        msg.setWindowTitle("Reporte Generado")
        msg.setText(f"El reporte se generó exitosamente en:\n{path}")
        msg.setIcon(QMessageBox.Icon.Information)
        
        btn_abrir = msg.addButton("Abrir Carpeta", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Aceptar", QMessageBox.ButtonRole.AcceptRole)
        
        msg.exec()
        
        if msg.clickedButton() == btn_abrir:
            folder = os.path.dirname(os.path.abspath(path))
            os.startfile(folder)

    def _mostrar_error(self, error):
        QMessageBox.critical(self, "Error", f"No se pudo generar el reporte:\n{error}")
