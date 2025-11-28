from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QTextEdit, QSplitter, QGroupBox)
from PyQt6.QtCore import Qt
import json
from models.database_model import obtener_session, Auditoria, Usuario

class AuditoriaWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.cargar_datos()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🕵️ Auditoría del Sistema")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a73e8;")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tabla de Logs
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Usuario", "Acción", "Tabla", "ID Registro"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.itemSelectionChanged.connect(self.mostrar_detalle)
        
        splitter.addWidget(self.tabla)

        # Panel de Detalles
        grp_detalles = QGroupBox("Detalles del Cambio")
        layout_det = QVBoxLayout()
        self.txt_detalles = QTextEdit()
        self.txt_detalles.setReadOnly(True)
        layout_det.addWidget(self.txt_detalles)
        grp_detalles.setLayout(layout_det)
        
        splitter.addWidget(grp_detalles)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter)
        self.setLayout(layout)

    def cargar_datos(self):
        logs = self.session.query(Auditoria).order_by(Auditoria.fecha.desc()).limit(100).all()
        self.tabla.setRowCount(len(logs))
        
        for row, log in enumerate(logs):
            self.tabla.setItem(row, 0, QTableWidgetItem(str(log.fecha)))
            
            usuario = "Sistema"
            if log.usuario_id:
                u = self.session.query(Usuario).get(log.usuario_id)
                if u: usuario = u.username
            
            self.tabla.setItem(row, 1, QTableWidgetItem(usuario))
            self.tabla.setItem(row, 2, QTableWidgetItem(log.accion))
            self.tabla.setItem(row, 3, QTableWidgetItem(log.tabla or "-"))
            self.tabla.setItem(row, 4, QTableWidgetItem(str(log.registro_id or "-")))
            
            # Guardar el objeto log en el item para recuperarlo luego
            self.tabla.item(row, 0).setData(Qt.ItemDataRole.UserRole, log)

    def mostrar_detalle(self):
        items = self.tabla.selectedItems()
        if not items: return
        
        log = items[0].data(Qt.ItemDataRole.UserRole)
        if not log or not log.detalles:
            self.txt_detalles.setText("Sin detalles adicionales.")
            return

        try:
            # Intentar parsear JSON
            data = json.loads(log.detalles)
            texto = json.dumps(data, indent=4, ensure_ascii=False)
            self.txt_detalles.setText(texto)
        except:
            # Si no es JSON, mostrar texto plano
            self.txt_detalles.setText(log.detalles)
