"""
Gestión de Clientes - Sistema Kardex Valorizado
Archivo: src/views/clientes_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QTextEdit, QMessageBox, QDialog,
                              QFormLayout, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Cliente
from sqlalchemy import or_
from utils.widgets import UpperLineEdit
from utils.button_utils import style_button


class ClienteDialog(QDialog):
    """Diálogo para crear/editar clientes"""

    def __init__(self, parent=None, cliente=None, session=None):
        super().__init__(parent)
        self.session = session if session else obtener_session()
        self.cliente = cliente
        self.init_ui()

        if cliente:
            self.cargar_datos_cliente()

    def init_ui(self):
        self.setWindowTitle("Nuevo Cliente" if not self.cliente else "Editar Cliente")
        self.setFixedSize(550, 500)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel { color: #333; }
            QLineEdit, QTextEdit { padding: 8px; border: 2px solid #ddd; border-radius: 4px; background-color: white; font-size: 11px; }
            QLineEdit:focus, QTextEdit:focus { border: 2px solid #1a73e8; }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        titulo = QLabel("👤 " + ("Nuevo Cliente" if not self.cliente else "Editar Cliente"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)

        form_layout = QFormLayout()
        self.lbl_id_etiqueta = QLabel("ID Interno:")
        self.txt_id_display = QLineEdit()
        self.txt_id_display.setEnabled(False)
        self.txt_id_display.setStyleSheet("background-color: #eee; color: #555; font-weight: bold;")
        self.lbl_id_etiqueta.hide()
        self.txt_id_display.hide()
        form_layout.addRow(self.lbl_id_etiqueta, self.txt_id_display)
        form_layout.setSpacing(12)

        self.txt_ruc_o_dni = QLineEdit()
        self.txt_ruc_o_dni.setMaxLength(11)
        self.txt_ruc_o_dni.setPlaceholderText("Ingrese RUC (11) o DNI (8)")
        self.txt_ruc_o_dni.textChanged.connect(self.validar_identificador)
        form_layout.addRow("RUC/DNI:*", self.txt_ruc_o_dni)

        self.lbl_validacion = QLabel()
        self.lbl_validacion.setStyleSheet("color: #ea4335; font-size: 10px;")
        form_layout.addRow("", self.lbl_validacion)

        self.txt_razon_social = UpperLineEdit()
        self.txt_razon_social.setPlaceholderText("Razón social o nombre completo")
        form_layout.addRow("Razón Social/Nombre:*", self.txt_razon_social)

        self.txt_direccion = QTextEdit()
        self.txt_direccion.setMaximumHeight(60)
        self.txt_direccion.setPlaceholderText("Dirección fiscal o de contacto")
        form_layout.addRow("Dirección:", self.txt_direccion)

        self.txt_telefono = UpperLineEdit()
        self.txt_telefono.setPlaceholderText("Teléfono de contacto")
        form_layout.addRow("Teléfono:", self.txt_telefono)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("correo@empresa.com")
        form_layout.addRow("Email:", self.txt_email)

        self.txt_contacto = UpperLineEdit()
        self.txt_contacto.setPlaceholderText("Nombre de la persona de contacto")
        form_layout.addRow("Persona Contacto:", self.txt_contacto)

        layout.addLayout(form_layout)
        nota = QLabel("* Campos obligatorios")
        nota.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        layout.addWidget(nota)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.clicked.connect(self.guardar)
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4: self.guardar()
        else: super().keyPressEvent(event)

    def validar_identificador(self, texto):
        identificador = re.sub(r'\D', '', texto)
        if not identificador:
            self.lbl_validacion.setText("")
            self.btn_guardar.setEnabled(True)
            return

        if len(identificador) not in [8, 11]:
            self.lbl_validacion.setText("⚠️ Debe ser un DNI (8) o RUC (11)")
            self.btn_guardar.setEnabled(False)
            return

        query = self.session.query(Cliente).filter_by(ruc_o_dni=identificador)
        if self.cliente:
            query = query.filter(Cliente.id != self.cliente.id)
        if query.first():
            self.lbl_validacion.setText("❌ Este número ya está registrado")
            self.btn_guardar.setEnabled(False)
            return

        self.lbl_validacion.setText("✓ Válido")
        self.lbl_validacion.setStyleSheet("color: #34a853; font-size: 10px;")
        self.btn_guardar.setEnabled(True)

    def cargar_datos_cliente(self):
        if self.cliente.id:
            self.txt_id_display.setText(str(self.cliente.id))
            self.lbl_id_etiqueta.show()
            self.txt_id_display.show()
        self.txt_ruc_o_dni.setText(self.cliente.ruc_o_dni)
        self.txt_razon_social.setText(self.cliente.razon_social_o_nombre)
        self.txt_direccion.setPlainText(self.cliente.direccion or "")
        self.txt_telefono.setText(self.cliente.telefono or "")
        self.txt_email.setText(self.cliente.email or "")
        self.txt_contacto.setText(self.cliente.contacto or "")

    def guardar(self):
        ruc_o_dni = self.txt_ruc_o_dni.text().strip()
        razon_social = self.txt_razon_social.text().strip()
        if len(ruc_o_dni) not in [8, 11]:
            QMessageBox.warning(self, "Error", "El RUC/DNI debe tener 8 u 11 dígitos")
            return
        if not razon_social:
            QMessageBox.warning(self, "Error", "La Razón Social/Nombre es obligatoria")
            return
        email = self.txt_email.text().strip()
        if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            QMessageBox.warning(self, "Error", "El email no es válido")
            return

        try:
            if not self.cliente:
                cliente = Cliente(
                    ruc_o_dni=ruc_o_dni,
                    razon_social_o_nombre=razon_social,
                    direccion=self.txt_direccion.toPlainText() or None,
                    telefono=self.txt_telefono.text().strip() or None,
                    email=email or None,
                    contacto=self.txt_contacto.text().strip() or None
                )
                self.session.add(cliente)
                mensaje = f"Cliente {razon_social} creado exitosamente"
            else:
                self.cliente.ruc_o_dni = ruc_o_dni
                self.cliente.razon_social_o_nombre = razon_social
                self.cliente.direccion = self.txt_direccion.toPlainText() or None
                self.cliente.telefono = self.txt_telefono.text().strip() or None
                self.cliente.email = email or None
                self.cliente.contacto = self.txt_contacto.text().strip() or None
                mensaje = f"Cliente {razon_social} actualizado exitosamente"

            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")

class ClientesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.clientes_mostrados = []
        self.init_ui()
        self.cargar_clientes()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2: self.nuevo_cliente()
        elif event.key() == Qt.Key.Key_F6:
            fila = self.tabla.currentRow()
            if fila != -1 and fila < len(self.clientes_mostrados):
                self.editar_cliente(self.clientes_mostrados[fila])
        else: super().keyPressEvent(event)

    def init_ui(self):
        self.setWindowTitle("Gestión de Clientes")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        titulo = QLabel("👤 Gestión de Clientes")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        btn_nuevo = QPushButton()
        style_button(btn_nuevo, 'add', "Nuevo Cliente")
        btn_nuevo.clicked.connect(self.nuevo_cliente)
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nuevo)

        self.txt_buscar = UpperLineEdit()
        self.txt_buscar.setClearButtonEnabled(True)
        self.txt_buscar.setPlaceholderText("🔍 Buscar por RUC/DNI, Razón Social/Nombre o contacto...")
        self.txt_buscar.textChanged.connect(self.buscar_clientes)

        self.lbl_contador = QLabel()
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels(["ID", "RUC/DNI", "Razón Social/Nombre", "Teléfono", "Email", "Contacto", "Dirección", "Acciones"])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(7, 150)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addLayout(header_layout)
        layout.addWidget(self.txt_buscar)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)
        self.setLayout(layout)

    def cargar_clientes(self):
        clientes = self.session.query(Cliente).filter_by(activo=True).order_by(Cliente.razon_social_o_nombre).all()
        self.mostrar_clientes(clientes)

    def mostrar_clientes(self, clientes):
        self.clientes_mostrados = clientes
        self.tabla.setRowCount(len(clientes))
        for row, cli in enumerate(clientes):
            self.tabla.setItem(row, 0, QTableWidgetItem(str(cli.id)))
            self.tabla.setItem(row, 1, QTableWidgetItem(cli.ruc_o_dni))
            self.tabla.setItem(row, 2, QTableWidgetItem(cli.razon_social_o_nombre))
            self.tabla.setItem(row, 3, QTableWidgetItem(cli.telefono or ""))
            self.tabla.setItem(row, 4, QTableWidgetItem(cli.email or ""))
            self.tabla.setItem(row, 5, QTableWidgetItem(cli.contacto or ""))
            self.tabla.setItem(row, 6, QTableWidgetItem(cli.direccion or ""))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 5, 5, 5)
            btn_editar = QPushButton()
            style_button(btn_editar, 'edit', "Editar")
            btn_editar.clicked.connect(lambda checked, c=cli: self.editar_cliente(c))
            btn_eliminar = QPushButton()
            style_button(btn_eliminar, 'delete', "Eliminar")
            btn_eliminar.clicked.connect(lambda checked, c=cli: self.eliminar_cliente(c))
            btn_layout.addWidget(btn_editar)
            btn_layout.addWidget(btn_eliminar)
            btn_widget.setLayout(btn_layout)
            self.tabla.setCellWidget(row, 7, btn_widget)

        self.lbl_contador.setText(f"📊 Total: {len(clientes)} cliente(es)")

    def buscar_clientes(self):
        texto = self.txt_buscar.text().lower().strip()
        query = self.session.query(Cliente).filter_by(activo=True)
        if texto:
            filtro_texto = f"%{texto}%"
            query = query.filter(or_(
                Cliente.ruc_o_dni.ilike(filtro_texto),
                Cliente.razon_social_o_nombre.ilike(filtro_texto),
                Cliente.contacto.ilike(filtro_texto)
            ))
        self.mostrar_clientes(query.order_by(Cliente.razon_social_o_nombre).all())

    def nuevo_cliente(self):
        dialog = ClienteDialog(self, session=self.session)
        if dialog.exec() == QDialog.DialogCode.Accepted: self.cargar_clientes()

    def editar_cliente(self, cliente):
        dialog = ClienteDialog(self, cliente=cliente, session=self.session)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(cliente)
            self.cargar_clientes()

    def eliminar_cliente(self, cliente):
        respuesta = QMessageBox.question(self, "Confirmar eliminación",
            f"¿Está seguro de eliminar al cliente:\n{cliente.ruc_o_dni} - {cliente.razon_social_o_nombre}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                cliente.activo = False
                self.session.commit()
                QMessageBox.information(self, "Éxito", "Cliente eliminado correctamente")
                self.cargar_clientes()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error al eliminar:\n{str(e)}")

    def closeEvent(self, event):
        try:
            self.session.close()
        finally:
            event.accept()
