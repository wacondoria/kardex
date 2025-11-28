"""
Gestión de Proyectos - Sistema Kardex Valorizado
Archivo: src/views/proyectos_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QTextEdit, QMessageBox, QDialog,
                              QFormLayout, QHeaderView, QComboBox, QDateEdit,
                              QDoubleSpinBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Proyecto, Cliente, Empresa, EstadoProyecto
from sqlalchemy import or_
from utils.widgets import UpperLineEdit
from utils.button_utils import style_button
from views.base_crud_view import BaseCRUDView


class ProyectoDialog(QDialog):
    """Diálogo para crear/editar proyectos"""

    def __init__(self, parent=None, proyecto=None, session=None):
        super().__init__(parent)
        self.session = session if session else obtener_session()
        self.proyecto = proyecto
        self.init_ui()

        if proyecto:
            self.cargar_datos_proyecto()
        else:
            self.txt_fecha_inicio.setDate(QDate.currentDate())

    def init_ui(self):
        self.setWindowTitle("Nuevo Proyecto" if not self.proyecto else "Editar Proyecto")
        self.setFixedSize(600, 650)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel { color: #333; }
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QDoubleSpinBox { 
                padding: 8px; border: 2px solid #ddd; border-radius: 4px; background-color: white; font-size: 11px; 
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 2px solid #1a73e8; }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        titulo = QLabel("🏗️ " + ("Nuevo Proyecto" if not self.proyecto else "Editar Proyecto"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # ID (Hidden)
        self.txt_id_display = QLineEdit()
        self.txt_id_display.setEnabled(False)
        self.txt_id_display.hide()
        
        # Código
        self.txt_codigo = UpperLineEdit()
        self.txt_codigo.setPlaceholderText("Ej: PRJ-2023-001")
        form_layout.addRow("Código:*", self.txt_codigo)

        # Nombre
        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre del Proyecto / Obra")
        form_layout.addRow("Nombre:*", self.txt_nombre)

        # Cliente
        self.cmb_cliente = QComboBox()
        self.cargar_clientes()
        form_layout.addRow("Cliente:*", self.cmb_cliente)

        # Ubicación
        self.txt_ubicacion = QLineEdit()
        self.txt_ubicacion.setPlaceholderText("Dirección o Ubicación de la Obra")
        form_layout.addRow("Ubicación:", self.txt_ubicacion)

        # Fechas
        self.txt_fecha_inicio = QDateEdit()
        self.txt_fecha_inicio.setCalendarPopup(True)
        self.txt_fecha_inicio.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Fecha Inicio:*", self.txt_fecha_inicio)

        self.txt_fecha_fin = QDateEdit()
        self.txt_fecha_fin.setCalendarPopup(True)
        self.txt_fecha_fin.setDisplayFormat("dd/MM/yyyy")
        self.txt_fecha_fin.setSpecialValueText(" ") # Allow empty-ish
        form_layout.addRow("Fecha Fin Est.:", self.txt_fecha_fin)

        # Presupuesto
        self.spin_presupuesto = QDoubleSpinBox()
        self.spin_presupuesto.setRange(0, 99999999.99)
        self.spin_presupuesto.setPrefix("S/ ")
        self.spin_presupuesto.setDecimals(2)
        form_layout.addRow("Presupuesto:", self.spin_presupuesto)

        # Estado
        self.cmb_estado = QComboBox()
        for estado in EstadoProyecto:
            self.cmb_estado.addItem(estado.value)
        form_layout.addRow("Estado:", self.cmb_estado)

        # Descripción
        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(80)
        form_layout.addRow("Descripción:", self.txt_descripcion)

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

        style_button(btn_cancelar, 'view', "Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton { background-color: #f1f3f4; color: #333; padding: 10px 30px; border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #e8eaed; }
        """)
        style_button(self.btn_guardar, 'add', "Guardar")

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def cargar_clientes(self):
        self.cmb_cliente.clear()
        clientes = self.session.query(Cliente).filter_by(activo=True).all()
        for c in clientes:
            self.cmb_cliente.addItem(f"{c.ruc_o_dni} - {c.razon_social_o_nombre}", c.id)

    def cargar_datos_proyecto(self):
        self.txt_id_display.setText(str(self.proyecto.id))
        self.txt_codigo.setText(self.proyecto.codigo)
        self.txt_nombre.setText(self.proyecto.nombre)
        
        # Select Cliente
        index = self.cmb_cliente.findData(self.proyecto.cliente_id)
        if index >= 0:
            self.cmb_cliente.setCurrentIndex(index)
            
        self.txt_ubicacion.setText(self.proyecto.ubicacion or "")
        
        # Dates
        if self.proyecto.fecha_inicio:
            self.txt_fecha_inicio.setDate(QDate(self.proyecto.fecha_inicio.year, self.proyecto.fecha_inicio.month, self.proyecto.fecha_inicio.day))
        
        if self.proyecto.fecha_fin_estimada:
            self.txt_fecha_fin.setDate(QDate(self.proyecto.fecha_fin_estimada.year, self.proyecto.fecha_fin_estimada.month, self.proyecto.fecha_fin_estimada.day))
        else:
            # Clear date logic if needed, but QDateEdit doesn't support null easily without custom logic
            # We'll just set to current date or leave as is
            pass

        self.spin_presupuesto.setValue(self.proyecto.presupuesto_estimado or 0.0)
        self.cmb_estado.setCurrentText(self.proyecto.estado.value)
        self.txt_descripcion.setPlainText(self.proyecto.descripcion or "")

    def guardar(self):
        codigo = self.txt_codigo.text().strip()
        nombre = self.txt_nombre.text().strip()
        cliente_id = self.cmb_cliente.currentData()
        
        if not codigo or not nombre or not cliente_id:
            QMessageBox.warning(self, "Error", "Complete los campos obligatorios (*)")
            return

        # Check duplicate code
        query = self.session.query(Proyecto).filter_by(codigo=codigo)
        if self.proyecto:
            query = query.filter(Proyecto.id != self.proyecto.id)
        if query.first():
            QMessageBox.warning(self, "Error", "El código de proyecto ya existe")
            return

        try:
            # Get default empresa (assuming single tenant for now or first one)
            empresa = self.session.query(Empresa).first()
            if not empresa:
                QMessageBox.warning(self, "Error", "No hay una empresa registrada en el sistema")
                return

            fecha_inicio = self.txt_fecha_inicio.date().toPyDate()
            fecha_fin = self.txt_fecha_fin.date().toPyDate() if self.txt_fecha_fin.date().isValid() else None
            
            # If date is "special value" (empty), set to None. 
            # But QDateEdit default is valid. Let's assume valid for now.

            if not self.proyecto:
                proyecto = Proyecto(
                    empresa_id=empresa.id,
                    cliente_id=cliente_id,
                    codigo=codigo,
                    nombre=nombre,
                    ubicacion=self.txt_ubicacion.text().strip() or None,
                    fecha_inicio=fecha_inicio,
                    fecha_fin_estimada=fecha_fin,
                    presupuesto_estimado=self.spin_presupuesto.value(),
                    estado=EstadoProyecto(self.cmb_estado.currentText()),
                    descripcion=self.txt_descripcion.toPlainText() or None
                )
                self.session.add(proyecto)
                mensaje = "Proyecto creado exitosamente"
            else:
                self.proyecto.cliente_id = cliente_id
                self.proyecto.codigo = codigo
                self.proyecto.nombre = nombre
                self.proyecto.ubicacion = self.txt_ubicacion.text().strip() or None
                self.proyecto.fecha_inicio = fecha_inicio
                self.proyecto.fecha_fin_estimada = fecha_fin
                self.proyecto.presupuesto_estimado = self.spin_presupuesto.value()
                self.proyecto.estado = EstadoProyecto(self.cmb_estado.currentText())
                self.proyecto.descripcion = self.txt_descripcion.toPlainText() or None
                mensaje = "Proyecto actualizado exitosamente"

            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")


class ProyectosWindow(BaseCRUDView):
    def __init__(self):
        super().__init__("Gestión de Proyectos", Proyecto, ProyectoDialog)

    def init_ui(self):
        super().init_ui()
        self.txt_buscar.setPlaceholderText("🔍 Buscar por Código, Nombre o Cliente...")
        self.btn_nuevo.setText("+ Nuevo Proyecto")

    def setup_table_columns(self):
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels(["ID", "Código", "Nombre", "Cliente", "Estado", "Inicio", "Acciones"])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Codigo
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Nombre
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Cliente
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed) # Acciones
        self.tabla.setColumnWidth(6, 180)

    def apply_ordering(self, query):
        return query.order_by(Proyecto.fecha_inicio.desc())

    def fill_row(self, row, proj):
        self.tabla.setItem(row, 0, QTableWidgetItem(str(proj.id)))
        self.tabla.setItem(row, 1, QTableWidgetItem(proj.codigo))
        self.tabla.setItem(row, 2, QTableWidgetItem(proj.nombre))
        
        cliente_nombre = proj.cliente.razon_social_o_nombre if proj.cliente else "N/A"
        self.tabla.setItem(row, 3, QTableWidgetItem(cliente_nombre))
        
        # Estado with color
        item_estado = QTableWidgetItem(proj.estado.value)
        if proj.estado == EstadoProyecto.EJECUCION:
            item_estado.setForeground(Qt.GlobalColor.darkGreen)
            item_estado.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        elif proj.estado == EstadoProyecto.PLANIFICACION:
            item_estado.setForeground(Qt.GlobalColor.blue)
        self.tabla.setItem(row, 4, item_estado)
        
        fecha_str = proj.fecha_inicio.strftime("%d/%m/%Y") if proj.fecha_inicio else ""
        self.tabla.setItem(row, 5, QTableWidgetItem(fecha_str))

    def apply_search_filters(self, query, text):
        filtro_texto = f"%{text}%"
        return query.join(Cliente).filter(or_(
            Proyecto.codigo.ilike(filtro_texto),
            Proyecto.nombre.ilike(filtro_texto),
            Cliente.razon_social.ilike(filtro_texto)
        ))

    def _open_dialog(self, item=None):
        dialog = ProyectoDialog(self, proyecto=item, session=self.session)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if item: self.session.refresh(item)
            self.load_data()

    def delete_item(self, item):
        respuesta = QMessageBox.question(self, "Confirmar eliminación",
            f"¿Está seguro de eliminar el proyecto:\n{item.codigo} - {item.nombre}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                item.activo = False
                self.session.commit()
                QMessageBox.information(self, "Éxito", "Proyecto eliminado correctamente")
                self.load_data()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error al eliminar:\n{str(e)}")
