from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QDialog, QInputDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
from models.database_model import obtener_session, Equipo, Alquiler, EstadoAlquiler
from views.alquileres_window import AlquileresWindow, PartialReturnDialog
from views.equipos_window import EquipoDialog # Para ver detalle si se necesita

class WarehouseKioskWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Modo Kiosco - Almacén")
        self.showMaximized()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)
        
        # Title
        lbl_title = QLabel("📦 TERMINAL DE ALMACÉN")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("font-size: 32px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(lbl_title)
        
        # Buttons Grid
        grid = QHBoxLayout()
        grid.setSpacing(30)
        
        # Button Style
        btn_style = """
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 15px;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """
        
        # 1. Despacho (Salida)
        btn_despacho = QPushButton("📤\nDESPACHO\n(Salida de Equipos)")
        btn_despacho.setFixedSize(300, 300)
        btn_despacho.setStyleSheet(btn_style)
        btn_despacho.clicked.connect(self.abrir_despacho)
        grid.addWidget(btn_despacho)
        
        # 2. Recepción (Retorno)
        btn_recepcion = QPushButton("📥\nRECEPCIÓN\n(Devolución)")
        btn_recepcion.setFixedSize(300, 300)
        btn_recepcion.setStyleSheet(btn_style.replace("#3498db", "#2ecc71").replace("#2980b9", "#27ae60"))
        btn_recepcion.clicked.connect(self.abrir_recepcion)
        grid.addWidget(btn_recepcion)
        
        # 3. Consultar Equipo
        btn_consulta = QPushButton("🔍\nCONSULTAR\nEQUIPO")
        btn_consulta.setFixedSize(300, 300)
        btn_consulta.setStyleSheet(btn_style.replace("#3498db", "#f39c12").replace("#2980b9", "#d35400"))
        btn_consulta.clicked.connect(self.consultar_equipo)
        grid.addWidget(btn_consulta)
        
        layout.addLayout(grid)
        layout.addStretch()
        
        self.setLayout(layout)

    def abrir_despacho(self):
        # Por ahora, abrimos la ventana de alquileres completa
        # Idealmente sería una vista filtrada solo para "Por Despachar"
        self.w = AlquileresWindow()
        self.w.show()

    def abrir_recepcion(self):
        # Seleccionar Alquiler para devolución
        # Diálogo simple para buscar alquiler por cliente o contrato
        dialog = SelectRentalDialog(self)
        if dialog.exec():
            alquiler_id = dialog.selected_alquiler_id
            if alquiler_id:
                alquiler = self.session.get(Alquiler, alquiler_id)
                if alquiler:
                    # Usamos el PartialReturnDialog existente
                    ret_dialog = PartialReturnDialog(self, alquiler)
                    ret_dialog.exec()

    def consultar_equipo(self):
        codigo, ok = QInputDialog.getText(self, "Consultar Equipo", "Ingrese Código o Serie:")
        if ok and codigo:
            equipo = self.session.query(Equipo).filter(
                (Equipo.codigo == codigo) | (Equipo.serie == codigo) | (Equipo.codigo_unico == codigo)
            ).first()
            
            if equipo:
                msg = f"""
                <b>Equipo:</b> {equipo.nombre}<br>
                <b>Código:</b> {equipo.codigo}<br>
                <b>Estado:</b> {equipo.estado.value}<br>
                <b>Ubicación:</b> {equipo.almacen_id} (ID)<br>
                <b>Horómetro:</b> {equipo.horometro_actual}
                """
                QMessageBox.information(self, "Detalle Equipo", msg)
            else:
                QMessageBox.warning(self, "No encontrado", "No se encontró el equipo.")

class SelectRentalDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.selected_alquiler_id = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Seleccionar Alquiler")
        self.resize(600, 400)
        layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Contrato", "Cliente", "Obra"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        self.cargar_alquileres()
        
        btn = QPushButton("Seleccionar")
        btn.clicked.connect(self.seleccionar)
        layout.addWidget(btn)
        
        self.setLayout(layout)
        
    def cargar_alquileres(self):
        # Solo activos
        alquileres = self.session.query(Alquiler).filter(Alquiler.estado == EstadoAlquiler.ACTIVO).all()
        self.table.setRowCount(0)
        for row, a in enumerate(alquileres):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(a.id)))
            self.table.setItem(row, 1, QTableWidgetItem(a.numero_contrato))
            self.table.setItem(row, 2, QTableWidgetItem(a.cliente.razon_social_o_nombre))
            self.table.setItem(row, 3, QTableWidgetItem(a.ubicacion_obra or ""))
            
    def seleccionar(self):
        row = self.table.currentRow()
        if row >= 0:
            self.selected_alquiler_id = int(self.table.item(row, 0).text())
            self.accept()
        else:
            QMessageBox.warning(self, "Aviso", "Seleccione una fila.")
