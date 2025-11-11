"""
Gestión de Motivos de Ajuste - Sistema Kardex Valorizado
Archivo: src/views/motivos_ajuste_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QTextEdit, QMessageBox, QDialog,
                              QFormLayout, QHeaderView, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, MotivoAjuste, TipoAjuste
from sqlalchemy import or_
from utils.widgets import UpperLineEdit
from utils.button_utils import style_button

class MotivoAjusteDialog(QDialog):
    def __init__(self, parent=None, motivo=None, session=None):
        super().__init__(parent)
        self.session = session if session else obtener_session()
        self.motivo = motivo
        self.init_ui()
        if motivo:
            self.cargar_datos()

    def init_ui(self):
        self.setWindowTitle("Nuevo Motivo de Ajuste" if not self.motivo else "Editar Motivo de Ajuste")
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.txt_nombre = UpperLineEdit()
        self.txt_descripcion = QTextEdit()
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems([e.value for e in TipoAjuste])

        form_layout.addRow("Nombre:*", self.txt_nombre)
        form_layout.addRow("Descripción:", self.txt_descripcion)
        form_layout.addRow("Tipo de Ajuste:*", self.cmb_tipo)
        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.clicked.connect(self.guardar)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        layout.addLayout(btn_layout)

    def cargar_datos(self):
        self.txt_nombre.setText(self.motivo.nombre)
        self.txt_descripcion.setPlainText(self.motivo.descripcion or "")
        self.cmb_tipo.setCurrentText(self.motivo.tipo.value)

    def guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
            return

        try:
            if not self.motivo:
                self.motivo = MotivoAjuste()
                self.session.add(self.motivo)

            self.motivo.nombre = nombre
            self.motivo.descripcion = self.txt_descripcion.toPlainText().strip() or None
            self.motivo.tipo = TipoAjuste(self.cmb_tipo.currentText())

            self.session.commit()
            QMessageBox.information(self, "Éxito", "Motivo guardado correctamente.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar el motivo:\n{e}")

class MotivosAjusteWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.cargar_motivos()

    def init_ui(self):
        self.setWindowTitle("Gestión de Motivos de Ajuste")
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        titulo = QLabel("📝 Gestión de Motivos de Ajuste")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        btn_nuevo = QPushButton("Nuevo Motivo")
        btn_nuevo.clicked.connect(self.nuevo_motivo)
        header_layout.addWidget(btn_nuevo)
        layout.addLayout(header_layout)

        self.tabla = QTableWidget(columnCount=4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Tipo", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla)

    def cargar_motivos(self):
        motivos = self.session.query(MotivoAjuste).filter_by(activo=True).order_by(MotivoAjuste.nombre).all()
        self.tabla.setRowCount(len(motivos))
        for row, motivo in enumerate(motivos):
            self.tabla.setItem(row, 0, QTableWidgetItem(str(motivo.id)))
            self.tabla.setItem(row, 1, QTableWidgetItem(motivo.nombre))
            self.tabla.setItem(row, 2, QTableWidgetItem(motivo.tipo.value))

            btn_editar = QPushButton("Editar")
            btn_editar.clicked.connect(lambda _, m=motivo: self.editar_motivo(m))
            btn_eliminar = QPushButton("Eliminar")
            btn_eliminar.clicked.connect(lambda _, m=motivo: self.eliminar_motivo(m))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.addWidget(btn_editar)
            btn_layout.addWidget(btn_eliminar)
            btn_layout.setContentsMargins(0,0,0,0)
            self.tabla.setCellWidget(row, 3, btn_widget)

    def nuevo_motivo(self):
        dialog = MotivoAjusteDialog(self, session=self.session)
        if dialog.exec():
            self.cargar_motivos()

    def editar_motivo(self, motivo):
        dialog = MotivoAjusteDialog(self, motivo=motivo, session=self.session)
        if dialog.exec():
            self.cargar_motivos()

    def eliminar_motivo(self, motivo):
        reply = QMessageBox.question(self, "Confirmar", f"¿Eliminar el motivo '{motivo.nombre}'?")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                motivo.activo = False
                self.session.commit()
                self.cargar_motivos()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")

    def closeEvent(self, event):
        self.session.close()
        super().closeEvent(event)
