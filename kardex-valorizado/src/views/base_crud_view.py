"""
Base CRUD View - Sistema Kardex Valorizado
Archivo: src/views/base_crud_view.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QMessageBox, QDialog, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
from pathlib import Path

# Adjust path to import from parent directory if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session
from utils.widgets import UpperLineEdit
from utils.button_utils import style_button
from views.dialogs.delete_range_dialog import DeleteRangeDialog

class BaseCRUDView(QWidget):
    """
    Clase base para vistas CRUD (Clientes, Proveedores, Productos, etc.)
    """
    def __init__(self, title, model_class, dialog_class, parent=None):
        super().__init__(parent)
        self.title = title
        self.model_class = model_class
        self.dialog_class = dialog_class
        self.session = obtener_session()
        self.data_shown = []

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Inicializa la interfaz de usuario común."""
        self.setWindowTitle(self.title)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        titulo = QLabel(self.title)
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")

        self.btn_nuevo = QPushButton()
        # We can guess the button text, but it's better if subclasses customize it if needed
        # For now, standard text
        style_button(self.btn_nuevo, 'add', "Nuevo (F2)")
        self.btn_nuevo.clicked.connect(self.create_item)

        header_layout.addWidget(titulo)
        header_layout.addStretch()
        
        self.btn_eliminar_rango = QPushButton()
        style_button(self.btn_eliminar_rango, 'delete', "Eliminar Rango")
        self.btn_eliminar_rango.clicked.connect(self.eliminar_rango)
        header_layout.addWidget(self.btn_eliminar_rango)
        
        header_layout.addWidget(self.btn_nuevo)

        # Filter/Search Layout
        self.filter_layout = QHBoxLayout()

        self.txt_buscar = UpperLineEdit()
        self.txt_buscar.setClearButtonEnabled(True)
        self.txt_buscar.setPlaceholderText("🔍 Buscar...")
        self.txt_buscar.textChanged.connect(self.search_data)
        self.filter_layout.addWidget(self.txt_buscar, 3) # Give search bar more space

        self.add_extra_filters(self.filter_layout)

        # Counter
        self.lbl_contador = QLabel()
        self.lbl_contador.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")

        # Table
        self.tabla = QTableWidget()
        self.setup_table_columns()
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addLayout(header_layout)
        layout.addLayout(self.filter_layout)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)
        self.setLayout(layout)

    def add_extra_filters(self, layout):
        """Override to add more filters to the search bar area"""
        pass

    def setup_table_columns(self):
        """Override to set column count and headers"""
        raise NotImplementedError("Subclasses must implement setup_table_columns")

    def load_data(self):
        """Default implementation: query all active items"""
        try:
            # Handle cases where session might be expired or closed
            if not self.session.is_active:
                self.session = obtener_session()
            else:
                self.session.expire_all()

            query = self.get_base_query()
            query = self.apply_ordering(query)

            items = query.all()
            self.show_data(items)
        except Exception as e:
            print(f"Error loading data in {self.title}: {e}")
            self.session.rollback()

    def get_base_query(self):
        """Returns the base query, filtering by active status if applicable."""
        if hasattr(self.model_class, 'activo'):
            return self.session.query(self.model_class).filter_by(activo=True)
        return self.session.query(self.model_class)

    def apply_ordering(self, query):
        """Override to apply default ordering"""
        return query

    def show_data(self, items):
        self.data_shown = items
        self.tabla.setRowCount(len(items))
        self.lbl_contador.setText(f"📊 Total: {len(items)}")

        for row, item in enumerate(items):
            self.fill_row(row, item)
            self.add_action_buttons(row, item)

    def fill_row(self, row, item):
        """Override to fill specific columns"""
        raise NotImplementedError("Subclasses must implement fill_row")

    def add_action_buttons(self, row, item):
        btn_widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(5, 5, 5, 5)
        btn_layout.setSpacing(5)

        btn_editar = QPushButton()
        style_button(btn_editar, 'edit', "Editar")
        btn_editar.clicked.connect(lambda checked, i=item: self.edit_item(i))

        btn_eliminar = QPushButton()
        style_button(btn_eliminar, 'delete', "Eliminar")
        btn_eliminar.clicked.connect(lambda checked, i=item: self.delete_item(i))

        self.customize_buttons(btn_layout, item, btn_editar, btn_eliminar)

        btn_layout.addWidget(btn_editar)
        btn_layout.addWidget(btn_eliminar)
        btn_layout.addStretch() # Align left
        btn_widget.setLayout(btn_layout)

        # Assuming the last column is for actions
        self.tabla.setCellWidget(row, self.tabla.columnCount() - 1, btn_widget)

    def customize_buttons(self, layout, item, btn_edit, btn_delete):
        """Override to add or remove buttons, or disable them"""
        pass

    def search_data(self):
        """Override to implement search logic"""
        text = self.txt_buscar.text().strip()

        try:
            query = self.get_base_query()

            if text:
                query = self.apply_search_filters(query, text)

            # Apply extra filters from subclasses
            query = self.apply_extra_filters(query)

            query = self.apply_ordering(query)
            self.show_data(query.all())
        except Exception as e:
            print(f"Error searching data: {e}")

    def apply_search_filters(self, query, text):
        """Override to apply filters to the query based on text"""
        return query

    def apply_extra_filters(self, query):
        """Override to apply filters from extra widgets"""
        return query

    def create_item(self):
        self._open_dialog(None)

    def edit_item(self, item):
        self._open_dialog(item)

    def _open_dialog(self, item=None):
        """Opens the dialog. Subclasses must implement how to instantiate the dialog if it has custom args."""
        # This default implementation assumes a common signature: Dialog(parent, session=session, item=item)
        # But based on existing code:
        # ClienteDialog(parent, session=session) / (parent, cliente=cliente, session=session)
        # ProveedorDialog(parent, session=session) / (parent, proveedor=proveedor, session=session)
        # ProductoDialog(parent, producto=producto) -> session inside

        # We will rely on subclass override for instantiation, OR try to be smart.
        # For now, let's force subclasses to override `open_dialog_instance` or just `create/edit_item`.
        # Better: define a method that returns the dialog instance.
        pass

        # Implementation logic moved to subclasses for now because of signature differences.
        # However, we can define a standard way here if we fix the signatures.
        # Let's leave it abstract for a moment or provide a hook.

    def delete_item(self, item):
        """Default delete implementation (soft delete)"""
        reply = QMessageBox.question(self, "Confirmar eliminación",
            f"¿Está seguro de eliminar este elemento?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if hasattr(item, 'activo'):
                    item.activo = False
                else:
                    self.session.delete(item)
                self.session.commit()
                QMessageBox.information(self, "Éxito", "Elemento eliminado correctamente")
                self.load_data()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error al eliminar:\n{str(e)}")

    def eliminar_rango(self):
        """Elimina un rango de elementos por ID."""
        dialog = DeleteRangeDialog(self, title=f"Eliminar Rango - {self.title}", label_text="Ingrese el rango de IDs a eliminar:")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            desde, hasta = dialog.get_range()
            
            if not desde.isdigit() or not hasta.isdigit():
                QMessageBox.warning(self, "Error", "Para este módulo, los rangos deben ser numéricos (IDs).")
                return
                
            id_desde = int(desde)
            id_hasta = int(hasta)
            
            if id_desde > id_hasta:
                QMessageBox.warning(self, "Error", "El valor 'Desde' no puede ser mayor que 'Hasta'.")
                return
                
            confirm = QMessageBox.question(self, "Confirmar Eliminación Masiva", 
                                         f"¿Está SEGURO de eliminar los registros con ID del {id_desde} al {id_hasta}?\n\nEsta acción no se puede deshacer.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    query = self.session.query(self.model_class).filter(
                        self.model_class.id >= id_desde,
                        self.model_class.id <= id_hasta
                    )
                    
                    items = query.all()
                    count = len(items)
                    
                    if count == 0:
                        QMessageBox.information(self, "Aviso", "No se encontraron registros en ese rango.")
                        return
                        
                    for item in items:
                        if hasattr(item, 'activo'):
                            item.activo = False
                        else:
                            self.session.delete(item)
                            
                    self.session.commit()
                    QMessageBox.information(self, "Éxito", f"Se han eliminado {count} registros correctamente.")
                    self.load_data()
                    
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error al eliminar rango:\n{str(e)}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2:
            self.create_item()
        elif event.key() == Qt.Key.Key_F6:
            row = self.tabla.currentRow()
            if row != -1 and row < len(self.data_shown):
                self.edit_item(self.data_shown[row])
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        try:
            self.session.close()
        finally:
            event.accept()
