"""
Gestión de Empresas y Almacenes - Sistema Kardex Valorizado
Archivo: src/views/empresas_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QTextEdit, QComboBox, QMessageBox,
                              QDialog, QFormLayout, QHeaderView, QTabWidget,
                              QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, Empresa, Almacen,
                                   MetodoValuacion)
from utils.widgets import UpperLineEdit, SearchableComboBox
from utils.button_utils import style_button


class AlmacenDialog(QDialog):
    """Diálogo para crear/editar almacenes"""

    def __init__(self, parent=None, empresa_id=None, almacen=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.empresa_id = empresa_id
        self.almacen = almacen
        self.init_ui()

        if almacen:
            self.cargar_datos_almacen()

    def init_ui(self):
        self.setWindowTitle("Nuevo Almacén" if not self.almacen else "Editar Almacén")
        self.setFixedSize(500, 350)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        titulo = QLabel("📦 " + ("Nuevo Almacén" if not self.almacen else "Editar Almacén"))
        titulo.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)

        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Código
        self.txt_codigo = UpperLineEdit()
        self.txt_codigo.setMaxLength(20)
        self.txt_codigo.setPlaceholderText("Ej: ALM-01")
        form_layout.addRow("Código:*", self.txt_codigo)

        # Nombre
        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: Almacén Principal")
        form_layout.addRow("Nombre:*", self.txt_nombre)

        # Descripción
        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(60)
        self.txt_descripcion.setPlaceholderText("Descripción del almacén")
        form_layout.addRow("Descripción:", self.txt_descripcion)

        # Ubicación
        self.txt_ubicacion = UpperLineEdit()
        self.txt_ubicacion.setPlaceholderText("Ubicación física")
        form_layout.addRow("Ubicación:", self.txt_ubicacion)

        layout.addLayout(form_layout)
        layout.addStretch()

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)

        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
            }
        """)
        btn_guardar.clicked.connect(self.guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        """Captura la pulsación de teclas en el diálogo."""
        if event.key() == Qt.Key.Key_F4:
            self.guardar()
        else:
            super().keyPressEvent(event)

    def cargar_datos_almacen(self):
        """Carga datos del almacén en edición"""
        self.txt_codigo.setText(self.almacen.codigo)
        self.txt_nombre.setText(self.almacen.nombre)
        self.txt_descripcion.setPlainText(self.almacen.descripcion or "")
        self.txt_ubicacion.setText(self.almacen.ubicacion or "")

    def guardar(self):
        """Guarda el almacén"""
        codigo = self.txt_codigo.text().strip().upper()
        nombre = self.txt_nombre.text().strip()

        if not codigo or not nombre:
            QMessageBox.warning(self, "Error", "Código y nombre son obligatorios")
            return

        try:
            if not self.almacen:
                # Verificar que no exista el código
                existe = self.session.query(Almacen).filter_by(
                    empresa_id=self.empresa_id,
                    codigo=codigo
                ).first()

                if existe:
                    QMessageBox.warning(self, "Error", f"El código {codigo} ya existe")
                    return

                almacen = Almacen(
                    empresa_id=self.empresa_id,
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=self.txt_descripcion.toPlainText() or None,
                    ubicacion=self.txt_ubicacion.text().strip() or None
                )

                self.session.add(almacen)
                mensaje = "Almacén creado exitosamente"
            else:
                self.almacen.nombre = nombre
                self.almacen.descripcion = self.txt_descripcion.toPlainText() or None
                self.almacen.ubicacion = self.txt_ubicacion.text().strip() or None
                mensaje = "Almacén actualizado exitosamente"

            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")


class EmpresaDialog(QDialog):
    """Diálogo para crear/editar empresas"""

    def __init__(self, parent=None, empresa=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.empresa = empresa
        self.init_ui()

        if empresa:
            self.cargar_datos_empresa()

    def init_ui(self):
        self.setWindowTitle("Nueva Empresa" if not self.empresa else "Editar Empresa")
        self.setFixedSize(600, 550)
        self.setStyleSheet("""
            QLineEdit, QTextEdit, QComboBox {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #1a73e8;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        titulo = QLabel("🏢 " + ("Nueva Empresa" if not self.empresa else "Editar Empresa"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)

        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # RUC
        self.txt_ruc = QLineEdit()
        self.txt_ruc.setMaxLength(11)
        self.txt_ruc.setPlaceholderText("RUC de 11 dígitos")
        self.txt_ruc.textChanged.connect(self.validar_ruc)
        form_layout.addRow("RUC:*", self.txt_ruc)

        # Validación RUC
        self.lbl_ruc_validacion = QLabel()
        self.lbl_ruc_validacion.setStyleSheet("color: #ea4335; font-size: 10px;")
        form_layout.addRow("", self.lbl_ruc_validacion)

        # Razón Social
        self.txt_razon_social = UpperLineEdit()
        self.txt_razon_social.setPlaceholderText("Razón social de la empresa")
        form_layout.addRow("Razón Social:*", self.txt_razon_social)

        # Dirección
        self.txt_direccion = QTextEdit()
        self.txt_direccion.setMaximumHeight(60)
        self.txt_direccion.setPlaceholderText("Dirección fiscal")
        form_layout.addRow("Dirección:", self.txt_direccion)

        # Teléfono
        self.txt_telefono = UpperLineEdit()
        self.txt_telefono.setPlaceholderText("Teléfono")
        form_layout.addRow("Teléfono:", self.txt_telefono)

        # Email
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("correo@empresa.com")
        form_layout.addRow("Email:", self.txt_email)

        layout.addLayout(form_layout)

        # Método de Valuación
        grupo_valuacion = QGroupBox("Método de Valuación del Inventario")
        grupo_layout = QVBoxLayout()

        info_label = QLabel("Seleccione el método de valuación para el kardex:")
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        grupo_layout.addWidget(info_label)

        self.cmb_metodo = QComboBox()
        self.cmb_metodo.addItem("PEPS (FIFO) - Primero en Entrar, Primero en Salir", MetodoValuacion.PEPS.value)
        self.cmb_metodo.addItem("UEPS (LIFO) - Último en Entrar, Primero en Salir", MetodoValuacion.UEPS.value)
        self.cmb_metodo.addItem("Promedio Ponderado", MetodoValuacion.PROMEDIO_PONDERADO.value)

        grupo_layout.addWidget(self.cmb_metodo)
        grupo_valuacion.setLayout(grupo_layout)
        layout.addWidget(grupo_valuacion)

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
                border-radius: 5px;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
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
        """Valida el RUC"""
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
            if not ruc.startswith(('10', '15', '17', '20')):
                self.lbl_ruc_validacion.setText("⚠️ RUC inválido")
                self.btn_guardar.setEnabled(False)
                return

            if not self.empresa:
                existe = self.session.query(Empresa).filter_by(ruc=ruc).first()
                if existe:
                    self.lbl_ruc_validacion.setText("❌ Este RUC ya está registrado")
                    self.btn_guardar.setEnabled(False)
                    return

            self.lbl_ruc_validacion.setText("✓ RUC válido")
            self.lbl_ruc_validacion.setStyleSheet("color: #34a853; font-size: 10px;")
            self.btn_guardar.setEnabled(True)

    def cargar_datos_empresa(self):
        """Carga datos de la empresa en edición"""
        self.txt_ruc.setText(self.empresa.ruc)
        self.txt_ruc.setEnabled(False)

        self.txt_razon_social.setText(self.empresa.razon_social)
        self.txt_direccion.setPlainText(self.empresa.direccion or "")
        self.txt_telefono.setText(self.empresa.telefono or "")
        self.txt_email.setText(self.empresa.email or "")

        # Seleccionar método
        for i in range(self.cmb_metodo.count()):
            if self.cmb_metodo.itemData(i) == self.empresa.metodo_valuacion.value:
                self.cmb_metodo.setCurrentIndex(i)
                break

    def guardar(self):
        """Guarda la empresa"""
        ruc = self.txt_ruc.text().strip()
        razon_social = self.txt_razon_social.text().strip()

        if len(ruc) != 11 or not razon_social:
            QMessageBox.warning(self, "Error", "RUC y razón social son obligatorios")
            return

        metodo_str = self.cmb_metodo.currentData()
        metodo = MetodoValuacion(metodo_str)

        try:
            if not self.empresa:
                empresa = Empresa(
                    ruc=ruc,
                    razon_social=razon_social,
                    direccion=self.txt_direccion.toPlainText() or None,
                    telefono=self.txt_telefono.text().strip() or None,
                    email=self.txt_email.text().strip() or None,
                    metodo_valuacion=metodo
                )

                self.session.add(empresa)
                self.session.flush()  # Para obtener el ID

                # Crear almacén por defecto
                almacen_default = Almacen(
                    empresa_id=empresa.id,
                    codigo="ALM-01",
                    nombre="Almacén Principal",
                    descripcion="Almacén creado automáticamente"
                )
                self.session.add(almacen_default)

                mensaje = f"Empresa {razon_social} creada exitosamente\nSe creó el almacén principal automáticamente"
            else:
                self.empresa.razon_social = razon_social
                self.empresa.direccion = self.txt_direccion.toPlainText() or None
                self.empresa.telefono = self.txt_telefono.text().strip() or None
                self.empresa.email = self.txt_email.text().strip() or None
                self.empresa.metodo_valuacion = metodo

                mensaje = "Empresa actualizada exitosamente"

            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")


class EmpresasWindow(QWidget):
    """Ventana principal de gestión de empresas"""

    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.empresa_seleccionada = None
        self.empresas_mostradas = []
        self.almacenes_mostrados = []
        self.init_ui()
        self.cargar_empresas()

    def keyPressEvent(self, event):
        """Captura la pulsación de F2 para crear y F6 para editar."""
        if event.key() == Qt.Key.Key_F2:
            if self.tabs.currentIndex() == 0:
                self.nueva_empresa()
            elif self.tabs.currentIndex() == 1:
                self.nuevo_almacen()
        elif event.key() == Qt.Key.Key_F6:
            if self.tabs.currentIndex() == 0:  # Pestaña de Empresas
                fila = self.tabla_empresas.currentRow()
                if fila != -1 and fila < len(self.empresas_mostradas):
                    empresa_seleccionada = self.empresas_mostradas[fila]
                    self.editar_empresa(empresa_seleccionada)
            elif self.tabs.currentIndex() == 1:  # Pestaña de Almacenes
                fila = self.tabla_almacenes.currentRow()
                if fila != -1 and fila < len(self.almacenes_mostrados):
                    almacen_seleccionado = self.almacenes_mostrados[fila]
                    self.editar_almacen(almacen_seleccionado)
        else:
            super().keyPressEvent(event)

    def init_ui(self):
        self.setWindowTitle("Gestión de Empresas y Almacenes")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        titulo = QLabel("🏢 Gestión de Empresas")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")

        btn_nueva = QPushButton()
        style_button(btn_nueva, 'add', "Nueva Empresa")
        btn_nueva.clicked.connect(self.nueva_empresa)

        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nueva)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f1f3f4;
                padding: 10px 20px;
                margin-right: 5px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: white;
                font-weight: bold;
            }
        """)

        # Tab 1: Empresas
        tab_empresas = QWidget()
        empresas_layout = QVBoxLayout()

        self.tabla_empresas = QTableWidget()
        self.tabla_empresas.setColumnCount(6)
        self.tabla_empresas.setHorizontalHeaderLabels([
            "RUC", "Razón Social", "Método Valuación", "Teléfono", "Email", "Acciones"
        ])

        self.tabla_empresas.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f1f3f4;
                padding: 10px;
                font-weight: bold;
            }
        """)

        header_empresas = self.tabla_empresas.horizontalHeader()
        header_empresas.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_empresas.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla_empresas.setColumnWidth(5, 200)
        self.tabla_empresas.setAlternatingRowColors(True)
        self.tabla_empresas.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        empresas_layout.addWidget(self.tabla_empresas)
        tab_empresas.setLayout(empresas_layout)

        # Tab 2: Almacenes
        tab_almacenes = QWidget()
        almacenes_layout = QVBoxLayout()

        # Selector de empresa
        selector_layout = QHBoxLayout()
        lbl_empresa = QLabel("Empresa:")
        lbl_empresa.setFont(QFont("Arial", 11, QFont.Weight.Bold))

        self.cmb_empresa_almacenes = SearchableComboBox()
        self.cmb_empresa_almacenes.setStyleSheet("padding: 8px;")
        self.cmb_empresa_almacenes.currentIndexChanged.connect(self.cargar_almacenes)

        btn_nuevo_almacen = QPushButton()
        style_button(btn_nuevo_almacen, 'add', "Nuevo Almacén")
        btn_nuevo_almacen.clicked.connect(self.nuevo_almacen)

        selector_layout.addWidget(lbl_empresa)
        selector_layout.addWidget(self.cmb_empresa_almacenes, 1)
        selector_layout.addWidget(btn_nuevo_almacen)

        almacenes_layout.addLayout(selector_layout)

        self.tabla_almacenes = QTableWidget()
        self.tabla_almacenes.setColumnCount(5)
        self.tabla_almacenes.setHorizontalHeaderLabels([
            "Código", "Nombre", "Descripción", "Ubicación", "Acciones"
        ])

        self.tabla_almacenes.setStyleSheet("""
            QTableWidget {
                border: none;
            }
            QHeaderView::section {
                background-color: #f1f3f4;
                padding: 10px;
                font-weight: bold;
            }
        """)

        header_almacenes = self.tabla_almacenes.horizontalHeader()
        header_almacenes.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_almacenes.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tabla_almacenes.setColumnWidth(4, 150)
        self.tabla_almacenes.setAlternatingRowColors(True)

        almacenes_layout.addWidget(self.tabla_almacenes)
        tab_almacenes.setLayout(almacenes_layout)

        # Agregar tabs
        self.tabs.addTab(tab_empresas, "🏢 Empresas")
        self.tabs.addTab(tab_almacenes, "📦 Almacenes")

        layout.addLayout(header_layout)
        layout.addWidget(self.tabs)

        self.setLayout(layout)

    def cargar_empresas(self):
        """Carga todas las empresas"""
        empresas = self.session.query(Empresa).filter_by(activo=True).all()
        self.empresas_mostradas = empresas
        self.tabla_empresas.setRowCount(len(empresas))

        # Limpiar y cargar combo
        self.cmb_empresa_almacenes.clear()

        for row, emp in enumerate(empresas):
            self.tabla_empresas.setItem(row, 0, QTableWidgetItem(emp.ruc))
            self.tabla_empresas.setItem(row, 1, QTableWidgetItem(emp.razon_social))
            self.tabla_empresas.setItem(row, 2, QTableWidgetItem(emp.metodo_valuacion.value))
            self.tabla_empresas.setItem(row, 3, QTableWidgetItem(emp.telefono or ""))
            self.tabla_empresas.setItem(row, 4, QTableWidgetItem(emp.email or ""))

            # Botones
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 5, 5, 5)

            btn_editar = QPushButton()
            style_button(btn_editar, 'edit', "Editar")
            btn_editar.clicked.connect(lambda checked, e=emp: self.editar_empresa(e))

            btn_eliminar = QPushButton()
            style_button(btn_eliminar, 'delete', "Eliminar")
            btn_eliminar.clicked.connect(lambda checked, e=emp: self.eliminar_empresa(e))

            btn_layout.addWidget(btn_editar)
            btn_layout.addWidget(btn_eliminar)
            btn_widget.setLayout(btn_layout)

            self.tabla_empresas.setCellWidget(row, 5, btn_widget)

            # Agregar al combo
            self.cmb_empresa_almacenes.addItem(f"{emp.ruc} - {emp.razon_social}", emp.id)

        if empresas:
            self.cargar_almacenes()

    def cargar_almacenes(self):
        """Carga almacenes de la empresa seleccionada"""
        empresa_id = self.cmb_empresa_almacenes.currentData()

        if not empresa_id:
            self.tabla_almacenes.setRowCount(0)
            return

        almacenes = self.session.query(Almacen).filter_by(
            empresa_id=empresa_id,
            activo=True
        ).all()
        self.almacenes_mostrados = almacenes
        self.tabla_almacenes.setRowCount(len(almacenes))

        for row, alm in enumerate(almacenes):
            self.tabla_almacenes.setItem(row, 0, QTableWidgetItem(alm.codigo))
            self.tabla_almacenes.setItem(row, 1, QTableWidgetItem(alm.nombre))
            self.tabla_almacenes.setItem(row, 2, QTableWidgetItem(alm.descripcion or ""))
            self.tabla_almacenes.setItem(row, 3, QTableWidgetItem(alm.ubicacion or ""))

            # Botones
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 5, 5, 5)

            btn_editar = QPushButton()
            style_button(btn_editar, 'edit', "Editar")
            btn_editar.clicked.connect(lambda checked, a=alm: self.editar_almacen(a))

            btn_eliminar = QPushButton()
            style_button(btn_eliminar, 'delete', "Eliminar")
            btn_eliminar.clicked.connect(lambda checked, a=alm: self.eliminar_almacen(a))

            btn_layout.addWidget(btn_editar)
            btn_layout.addWidget(btn_eliminar)
            btn_widget.setLayout(btn_layout)

            self.tabla_almacenes.setCellWidget(row, 4, btn_widget)

    def nueva_empresa(self):
        """Abre diálogo para crear empresa"""
        dialog = EmpresaDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_empresas()

    def editar_empresa(self, empresa):
        """Abre diálogo para editar empresa"""
        dialog = EmpresaDialog(self, empresa)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(empresa)
            self.cargar_empresas()

    def eliminar_empresa(self, empresa):
        """Elimina (desactiva) una empresa"""
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar empresa:\n{empresa.ruc} - {empresa.razon_social}?\n\n"
            "Se desactivará con todo su historial.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                empresa.activo = False
                self.session.commit()
                QMessageBox.information(self, "Éxito", "Empresa eliminada")
                self.cargar_empresas()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", str(e))

    def nuevo_almacen(self):
        """Abre diálogo para crear almacén"""
        empresa_id = self.cmb_empresa_almacenes.currentData()

        if not empresa_id:
            QMessageBox.warning(self, "Error", "Seleccione una empresa")
            return

        dialog = AlmacenDialog(self, empresa_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_almacenes()

    def editar_almacen(self, almacen):
        """Abre diálogo para editar almacén"""
        dialog = AlmacenDialog(self, almacen.empresa_id, almacen)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(almacen)
            self.cargar_almacenes()

    def eliminar_almacen(self, almacen):
        """Elimina (desactiva) un almacén"""
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar almacén:\n{almacen.codigo} - {almacen.nombre}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                almacen.activo = False
                self.session.commit()
                QMessageBox.information(self, "Éxito", "Almacén eliminado")
                self.cargar_almacenes()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", str(e))


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    ventana = EmpresasWindow()
    ventana.resize(1200, 700)
    ventana.show()

    sys.exit(app.exec())
