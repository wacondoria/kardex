from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidgetItem, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QMessageBox,
                             QLineEdit, QDateEdit, QCheckBox, QTableWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from models.database_model import obtener_session, Operador
from views.base_crud_view import BaseCRUDView
from datetime import date

class OperadorDialog(QDialog):
    operador_guardado = pyqtSignal()

    def __init__(self, parent=None, operador=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.operador = operador
        self.init_ui()
        if self.operador:
            self.cargar_datos()

    def init_ui(self):
        self.setWindowTitle("Nuevo Operador" if not self.operador else "Editar Operador")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.txt_nombre = QLineEdit()
        self.txt_dni = QLineEdit()
        self.txt_licencia = QLineEdit()
        self.txt_categoria = QLineEdit()
        
        self.date_vencimiento = QDateEdit(date.today().replace(year=date.today().year + 1))
        self.date_vencimiento.setCalendarPopup(True)
        
        self.chk_activo = QCheckBox("Activo")
        self.chk_activo.setChecked(True)
        
        form.addRow("Nombre Completo:*", self.txt_nombre)
        form.addRow("DNI:*", self.txt_dni)
        form.addRow("Nro. Licencia:", self.txt_licencia)
        form.addRow("Categoría Licencia:", self.txt_categoria)
        form.addRow("Vencimiento Licencia:", self.date_vencimiento)
        form.addRow("Estado:", self.chk_activo)
        
        layout.addLayout(form)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.guardar)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def cargar_datos(self):
        self.txt_nombre.setText(self.operador.nombre)
        self.txt_dni.setText(self.operador.dni)
        self.txt_licencia.setText(self.operador.licencia_conducir or "")
        self.txt_categoria.setText(self.operador.categoria_licencia or "")
        if self.operador.vencimiento_licencia:
            self.date_vencimiento.setDate(self.operador.vencimiento_licencia)
        self.chk_activo.setChecked(self.operador.activo)

    def guardar(self):
        nombre = self.txt_nombre.text().strip()
        dni = self.txt_dni.text().strip()
        
        if not nombre or not dni:
            QMessageBox.warning(self, "Error", "Nombre y DNI son obligatorios.")
            return
            
        try:
            if not self.operador:
                self.operador = Operador(
                    nombre=nombre,
                    dni=dni
                )
                self.session.add(self.operador)
            else:
                self.operador.nombre = nombre
                self.operador.dni = dni
                
            self.operador.licencia_conducir = self.txt_licencia.text().strip()
            self.operador.categoria_licencia = self.txt_categoria.text().strip()
            self.operador.vencimiento_licencia = self.date_vencimiento.date().toPyDate()
            self.operador.activo = self.chk_activo.isChecked()
            
            self.session.commit()
            self.operador_guardado.emit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class OperadoresWindow(BaseCRUDView):
    def __init__(self):
        super().__init__("Gestión de Operadores", Operador, OperadorDialog)
        
    def setup_table_columns(self):
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "DNI", "Licencia", "Vencimiento", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
    def fill_row(self, row, item):
        self.tabla.setItem(row, 0, QTableWidgetItem(str(item.id)))
        self.tabla.setItem(row, 1, QTableWidgetItem(item.nombre))
        self.tabla.setItem(row, 2, QTableWidgetItem(item.dni))
        self.tabla.setItem(row, 3, QTableWidgetItem(item.licencia_conducir or "-"))
        
        venc = "-"
        if item.vencimiento_licencia:
            venc = item.vencimiento_licencia.strftime("%d/%m/%Y")
            # Check if expired
            if item.vencimiento_licencia < date.today():
                venc += " (VENCIDO)"
                
        item_venc = QTableWidgetItem(venc)
        if "VENCIDO" in venc:
            item_venc.setForeground(Qt.GlobalColor.red)
            
        self.tabla.setItem(row, 4, item_venc)

    def _open_dialog(self, item=None):
        dialog = OperadorDialog(self, operador=item)
        dialog.operador_guardado.connect(self.load_data)
        dialog.exec()
