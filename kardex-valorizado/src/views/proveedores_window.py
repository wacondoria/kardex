"""
Gestión de Proveedores - Sistema Kardex Valorizado
Archivo: src/views/proveedores_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QTextEdit, QMessageBox, QDialog,
                              QFormLayout, QHeaderView)
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
import re

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, Alignment, PatternFill
except ImportError:
    print("Error: La librería 'openpyxl' no está instalada.")
    print("Por favor, instálela con: pip install openpyxl")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Proveedor
from sqlalchemy import or_
from utils.widgets import UpperLineEdit
from utils.button_utils import style_button
from views.base_crud_view import BaseCRUDView


class ProveedorDialog(QDialog):
    """Diálogo para crear/editar proveedores"""

    def __init__(self, parent=None, proveedor=None, session=None):
        super().__init__(parent)
        if session:
            self.session = session
        else:
            # Fallback por si se llama incorrectamente (aunque no debería)
            self.session = obtener_session()
        self.proveedor = proveedor
        self.init_ui()

        if proveedor:
            self.cargar_datos_proveedor()

    def init_ui(self):
        self.setWindowTitle("Nuevo Proveedor" if not self.proveedor else "Editar Proveedor")
        self.setFixedSize(550, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            QLineEdit, QTextEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 11px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #1a73e8;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        titulo = QLabel("🏪 " + ("Nuevo Proveedor" if not self.proveedor else "Editar Proveedor"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)

        # Formulario
        form_layout = QFormLayout()
        self.lbl_id_etiqueta = QLabel("ID Interno:")
        self.txt_id_display = QLineEdit()
        self.txt_id_display.setEnabled(False)
        self.txt_id_display.setStyleSheet("background-color: #eee; color: #555; font-weight: bold;")

        # Ocultarlos por defecto (solo se muestran al editar)
        self.lbl_id_etiqueta.hide()
        self.txt_id_display.hide()

        form_layout.addRow(self.lbl_id_etiqueta, self.txt_id_display)
        form_layout.setSpacing(12)

        # RUC
        self.txt_ruc = QLineEdit()
        self.txt_ruc.setMaxLength(11)
        self.txt_ruc.setPlaceholderText("Ingrese RUC (11 dígitos)")
        self.txt_ruc.textChanged.connect(self.validar_ruc)
        form_layout.addRow("RUC:*", self.txt_ruc)

        # Mensaje de validación RUC
        self.lbl_ruc_validacion = QLabel()
        self.lbl_ruc_validacion.setStyleSheet("color: #ea4335; font-size: 10px;")
        form_layout.addRow("", self.lbl_ruc_validacion)

        # Razón Social
        self.txt_razon_social = UpperLineEdit()
        self.txt_razon_social.setPlaceholderText("Razón social o nombre comercial")
        form_layout.addRow("Razón Social:*", self.txt_razon_social)

        # Dirección
        self.txt_direccion = QTextEdit()
        self.txt_direccion.setMaximumHeight(60)
        self.txt_direccion.setPlaceholderText("Dirección fiscal")
        form_layout.addRow("Dirección:", self.txt_direccion)

        # Teléfono
        self.txt_telefono = UpperLineEdit()
        self.txt_telefono.setPlaceholderText("Teléfono de contacto")
        form_layout.addRow("Teléfono:", self.txt_telefono)

        # Email
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("correo@empresa.com")
        form_layout.addRow("Email:", self.txt_email)

        # Contacto
        self.txt_contacto = UpperLineEdit()
        self.txt_contacto.setPlaceholderText("Nombre de la persona de contacto")
        form_layout.addRow("Persona Contacto:", self.txt_contacto)

        layout.addLayout(form_layout)

        # Nota
        nota = QLabel("* Campos obligatorios")
        nota.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        layout.addWidget(nota)

        layout.addStretch()

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f4;
                color: #333;
                padding: 10px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e8eaed;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 10px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.btn_guardar.clicked.connect(self.guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        """Captura la pulsación de teclas en el diálogo."""
        if event.key() == Qt.Key.Key_F4:
            self.guardar()
        else:
            super().keyPressEvent(event)

    def validar_ruc(self, texto):
        """Valida el RUC en tiempo real"""
        # Eliminar todo lo que no sea número
        ruc = re.sub(r'\D', '', texto)

        if len(ruc) == 0:
            self.lbl_ruc_validacion.setText("")
            self.btn_guardar.setEnabled(True)
            return

        if len(ruc) < 11:
            self.lbl_ruc_validacion.setText("⚠️ El RUC debe tener 11 dígitos")
            self.btn_guardar.setEnabled(False)
            return

        if len(ruc) == 11:
            # Validar que empiece con 10, 15, 17 o 20
            if not ruc.startswith(('10', '15', '17', '20')):
                self.lbl_ruc_validacion.setText("⚠️ RUC inválido (debe empezar con 10, 15, 17 o 20)")
                self.btn_guardar.setEnabled(False)
                return

            # --- MODIFICADO: Verificar duplicados al crear Y editar ---
            query = self.session.query(Proveedor).filter_by(ruc=ruc)

            if self.proveedor:
                # Al editar, excluimos al proveedor actual de la búsqueda
                query = query.filter(Proveedor.id != self.proveedor.id)

            existe = query.first()
            if existe:
                self.lbl_ruc_validacion.setText("❌ Este RUC ya está registrado en otro proveedor")
                self.btn_guardar.setEnabled(False)
                return
            # --- FIN DE LA MODIFICACIÓN ---

            self.lbl_ruc_validacion.setText("✓ RUC válido")
            self.lbl_ruc_validacion.setStyleSheet("color: #34a853; font-size: 10px;")
            self.btn_guardar.setEnabled(True)

    def cargar_datos_proveedor(self):
        """Carga datos del proveedor en edición"""
        if self.proveedor.id:
            self.txt_id_display.setText(str(self.proveedor.id))
            self.lbl_id_etiqueta.show()
            self.txt_id_display.show()
        self.txt_ruc.setText(self.proveedor.ruc)

        self.txt_razon_social.setText(self.proveedor.razon_social)
        self.txt_direccion.setPlainText(self.proveedor.direccion or "")
        self.txt_telefono.setText(self.proveedor.telefono or "")
        self.txt_email.setText(self.proveedor.email or "")
        self.txt_contacto.setText(self.proveedor.contacto or "")

    def guardar(self):
        """Guarda el proveedor"""
        # Validaciones
        ruc = self.txt_ruc.text().strip()
        razon_social = self.txt_razon_social.text().strip()

        if len(ruc) != 11:
            QMessageBox.warning(self, "Error", "El RUC debe tener 11 dígitos")
            return

        if not razon_social:
            QMessageBox.warning(self, "Error", "La razón social es obligatoria")
            return

        # Validar email si lo ingresó
        email = self.txt_email.text().strip()
        if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            QMessageBox.warning(self, "Error", "El email no es válido")
            return

        try:
            if not self.proveedor:
                # Crear nuevo
                proveedor = Proveedor(
                    ruc=ruc,
                    razon_social=razon_social,
                    direccion=self.txt_direccion.toPlainText() or None,
                    telefono=self.txt_telefono.text().strip() or None,
                    email=email or None,
                    contacto=self.txt_contacto.text().strip() or None
                )

                self.session.add(proveedor)
                mensaje = f"Proveedor {razon_social} creado exitosamente"
            else:
                # Editar existente
                self.proveedor.ruc = ruc
                self.proveedor.razon_social = razon_social
                self.proveedor.direccion = self.txt_direccion.toPlainText() or None
                self.proveedor.telefono = self.txt_telefono.text().strip() or None
                self.proveedor.email = email or None
                self.proveedor.contacto = self.txt_contacto.text().strip() or None

                mensaje = f"Proveedor {razon_social} actualizado exitosamente"

            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")


class ProveedoresWindow(BaseCRUDView):
    """Ventana principal de gestión de proveedores"""

    def __init__(self):
        super().__init__("Gestión de Proveedores", Proveedor, ProveedorDialog)

    def init_ui(self):
        super().init_ui()
        self.txt_buscar.setPlaceholderText("🔍 Buscar por RUC, razón social o contacto...")
        self.btn_nuevo.setText("+ Nuevo Proveedor")

    def setup_table_columns(self):
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "RUC", "Razón Social", "Teléfono", "Email", "Contacto", "Dirección", "Acciones"
        ])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(7, 150)

    def apply_ordering(self, query):
        return query.order_by(Proveedor.razon_social)

    def fill_row(self, row, prov):
        item_id = QTableWidgetItem(str(prov.id))
        item_id.setFlags(item_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item_id.setForeground(Qt.GlobalColor.gray)
        self.tabla.setItem(row, 0, item_id)

        self.tabla.setItem(row, 1, QTableWidgetItem(prov.ruc))
        self.tabla.setItem(row, 2, QTableWidgetItem(prov.razon_social))
        self.tabla.setItem(row, 3, QTableWidgetItem(prov.telefono or ""))
        self.tabla.setItem(row, 4, QTableWidgetItem(prov.email or ""))
        self.tabla.setItem(row, 5, QTableWidgetItem(prov.contacto or ""))
        self.tabla.setItem(row, 6, QTableWidgetItem(prov.direccion or ""))

    def apply_search_filters(self, query, text):
        filtro_texto = f"%{text}%"
        return query.filter(
            or_(
                Proveedor.ruc.ilike(filtro_texto),
                Proveedor.razon_social.ilike(filtro_texto),
                Proveedor.contacto.ilike(filtro_texto),
                Proveedor.email.ilike(filtro_texto)
            )
        )

    def _open_dialog(self, item=None):
        dialog = ProveedorDialog(self, proveedor=item, session=self.session)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if item: self.session.refresh(item)
            self.load_data()

    def delete_item(self, proveedor):
        # Override to provide specific message
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Está seguro de eliminar el proveedor:\n{proveedor.ruc} - {proveedor.razon_social}?\n\n"
            "El proveedor se desactivará pero se mantendrá en el historial.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                proveedor.activo = False
                self.session.commit()
                QMessageBox.information(self, "Éxito", "Proveedor eliminado correctamente")
                self.load_data()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error al eliminar:\n{str(e)}")

# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    ventana = ProveedoresWindow()
    ventana.resize(1200, 700)
    ventana.show()

    sys.exit(app.exec())
