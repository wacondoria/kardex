from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFormLayout)
from PyQt6.QtCore import Qt

class DeleteRangeDialog(QDialog):
    def __init__(self, parent=None, title="Eliminar Rango", label_text="Ingrese el rango a eliminar:"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(label_text))
        
        form_layout = QFormLayout()
        
        self.txt_desde = QLineEdit()
        self.txt_desde.setPlaceholderText("Desde (Ej: 001)")
        
        self.txt_hasta = QLineEdit()
        self.txt_hasta.setPlaceholderText("Hasta (Ej: 010)")
        
        form_layout.addRow("Desde:", self.txt_desde)
        form_layout.addRow("Hasta:", self.txt_hasta)
        
        layout.addLayout(form_layout)
        
        # Warning label
        lbl_warning = QLabel("⚠️ Esta acción eliminará todos los registros en el rango seleccionado y NO se puede deshacer.")
        lbl_warning.setWordWrap(True)
        lbl_warning.setStyleSheet("color: #ea4335; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_warning)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_confirm = QPushButton("Eliminar")
        self.btn_confirm.setStyleSheet("background-color: #ea4335; color: white; font-weight: bold;")
        self.btn_confirm.clicked.connect(self.validate_and_accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        
        layout.addLayout(btn_layout)
        
    def validate_and_accept(self):
        desde = self.txt_desde.text().strip()
        hasta = self.txt_hasta.text().strip()
        
        if not desde or not hasta:
            QMessageBox.warning(self, "Error", "Debe ingresar ambos valores (Desde y Hasta).")
            return
            
        self.accept()
        
    def get_range(self):
        return self.txt_desde.text().strip(), self.txt_hasta.text().strip()
