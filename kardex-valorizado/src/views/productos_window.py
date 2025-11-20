"""
Gestión de Productos - Sistema Kardex Valorizado
Archivo: src/views/productos_window.py
(Versión refactorizada usando BaseCRUDView)
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                             QTextEdit, QCheckBox, QMessageBox, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QRegularExpression
from PyQt6.QtGui import QFont, QKeyEvent, QRegularExpressionValidator
import sys
from pathlib import Path

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    print("Error: La librería 'openpyxl' no está instalada.")
    print("Por favor, instálela con: pip install openpyxl")
    sys.exit(1)

from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from models.database_model import obtener_session, Producto, Categoria, MovimientoStock
except ImportError:
    from models.database_model import obtener_session, Producto, Categoria
    MovimientoStock = None
from utils.widgets import UpperLineEdit, SearchableComboBox
from utils.button_utils import style_button
from views.base_crud_view import BaseCRUDView

UNIDADES_SUNAT = [
    "UND - Unidad", "KG - Kilogramo", "GR - Gramo", "LT - Litro",
    "ML - Mililitro", "M - Metro", "M2 - Metro cuadrado", "M3 - Metro cúbico",
    "CJ - Caja", "PQ - Paquete", "BOL - Bolsa", "SAC - Saco",
    "GLN - Galón", "DOC - Docena", "MIL - Millar"
]

def generar_codigo_completo(session, prefijo):
    """Genera el código completo con numeración automática"""
    ultimo = session.query(Producto).filter(
        Producto.codigo.like(f"{prefijo}-%")
    ).order_by(Producto.codigo.desc()).first()

    if ultimo:
        numero = int(ultimo.codigo.split('-')[1]) + 1
    else:
        numero = 1

    return f"{prefijo}-{numero:06d}"


class ProductoDialog(QDialog):
    """Diálogo para crear/editar productos"""

    producto_guardado = pyqtSignal()

    def __init__(self, parent=None, producto=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.producto = producto
        self.nuevo_producto_id = None
        self.init_ui()

        if producto:
            self.cargar_datos_producto()
        else:
            self.cmb_codigo.setCurrentIndex(-1)
            self.cmb_nombre.lineEdit().setPlaceholderText("Escriba un nombre o seleccione uno")
            self.cmb_nombre.setCurrentIndex(-1)

    def init_ui(self):
        self.setWindowTitle("Nuevo Producto" if not self.producto else "Editar Producto")
        self.setFixedSize(600, 650)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5ff5; }
            QLabel { color: #333; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                padding: 8px; border: 2px solid #ddd; border-radius: 4px;
                background-color: white; font-size: 11px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #1a73e8;
            }
            QComboBox::placeholder { color: #999; }
            QComboBox QLineEdit::placeholder { color: #999; }

            QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
                background-color: #f0f0f0;
                color: #888;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        titulo = QLabel("📦 " + ("Nuevo Producto" if not self.producto else "Editar Producto"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # --- CÓDIGO PREFIJO ---
        codigo_layout = QHBoxLayout()
        self.cmb_codigo = SearchableComboBox()
        self.cmb_codigo.setPlaceholderText("Ej: TUBO0")
        self.cmb_codigo.setToolTip("Seleccione un prefijo existente o escriba uno nuevo (5 caracteres)")

        validator = QRegularExpressionValidator(QRegularExpression("[A-Z0-9]{5}"))
        self.cmb_codigo.lineEdit().setValidator(validator)
        self.cmb_codigo.lineEdit().textChanged.connect(lambda text: self.cmb_codigo.lineEdit().setText(text.upper()))

        self.cmb_codigo.currentTextChanged.connect(self.actualizar_siguiente_correlativo)
        self.cmb_codigo.currentTextChanged.connect(self.actualizar_nombres_por_prefijo)

        self.lbl_codigo_completo = QLabel("-...")
        self.lbl_codigo_completo.setStyleSheet("color: #666; font-weight: bold;")

        codigo_layout.addWidget(self.cmb_codigo)
        codigo_layout.addWidget(self.lbl_codigo_completo)
        codigo_layout.addStretch()

        form_layout.addRow("Código (Prefijo):*", codigo_layout)

        # --- NOMBRE ---
        self.cmb_nombre = SearchableComboBox()
        self.cmb_nombre.setToolTip("Escriba un nombre nuevo o seleccione uno existente para editarlo")
        self.cmb_nombre.lineEdit().textChanged.connect(lambda text: self.cmb_nombre.lineEdit().setText(text.upper()))
        form_layout.addRow("Nombre:*", self.cmb_nombre)

        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(80)
        self.txt_descripcion.setPlaceholderText("Descripción detallada del producto")
        form_layout.addRow("Descripción:", self.txt_descripcion)

        self.cmb_categoria = SearchableComboBox()
        self.cargar_categorias()
        form_layout.addRow("Categoría:*", self.cmb_categoria)

        self.cmb_unidad = SearchableComboBox()
        self.cmb_unidad.addItems(UNIDADES_SUNAT)
        form_layout.addRow("Unidad Medida:*", self.cmb_unidad)

        self.spn_stock_min = QDoubleSpinBox()
        self.spn_stock_min.setRange(0, 999999)
        self.spn_stock_min.setDecimals(2)
        form_layout.addRow("Stock Mínimo:", self.spn_stock_min)

        self.spn_precio_venta = QDoubleSpinBox()
        self.spn_precio_venta.setRange(0, 999999.99)
        self.spn_precio_venta.setDecimals(2)
        self.spn_precio_venta.setPrefix("S/ ")
        form_layout.addRow("Precio Venta:", self.spn_precio_venta)

        config_group = QGroupBox("Configuración")
        config_layout = QVBoxLayout()

        self.chk_tiene_lote = QCheckBox("Maneja Lotes")
        self.chk_tiene_serie = QCheckBox("Maneja Series")

        vencimiento_layout = QHBoxLayout()
        self.chk_tiene_vencimiento = QCheckBox("Tiene Vencimiento")
        self.spn_dias_vencimiento = QSpinBox()
        self.spn_dias_vencimiento.setRange(0, 3650)
        self.spn_dias_vencimiento.setSuffix(" días")
        self.spn_dias_vencimiento.setEnabled(False)

        self.chk_tiene_vencimiento.toggled.connect(self.spn_dias_vencimiento.setEnabled)

        vencimiento_layout.addWidget(self.chk_tiene_vencimiento)
        vencimiento_layout.addWidget(self.spn_dias_vencimiento)
        vencimiento_layout.addStretch()

        config_layout.addWidget(self.chk_tiene_lote)
        config_layout.addWidget(self.chk_tiene_serie)
        config_layout.addLayout(vencimiento_layout)

        config_group.setLayout(config_layout)

        layout.addLayout(form_layout)
        layout.addWidget(config_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.guardar)

        btn_cancelar.setStyleSheet("""
            QPushButton { background-color: #f1f3f4; color: #333; padding: 10px 30px;
                border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #e8eaed; }
        """)
        btn_guardar.setStyleSheet("""
            QPushButton { background-color: #1a73e8; color: white; padding: 10px 30px;
                border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #1557b0; }
        """)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4:
            self.guardar()
        else:
            super().keyPressEvent(event)

    def cargar_prefijos_existentes(self):
        try:
            codigos_tuplas = self.session.query(Producto.codigo).distinct().all()

            prefijos_set = set()
            for (codigo,) in codigos_tuplas:
                if codigo and '-' in codigo:
                    prefijo = codigo.split('-')[0]
                    if len(prefijo) == 5 and prefijo.isalnum():
                        prefijos_set.add(prefijo)

            prefijos_ordenados = sorted(list(prefijos_set))

            texto_actual = self.cmb_codigo.currentText()

            self.cmb_codigo.clear()
            self.cmb_codigo.addItems(prefijos_ordenados)

            if texto_actual in prefijos_ordenados:
                self.cmb_codigo.setCurrentText(texto_actual)
            else:
                self.cmb_codigo.setCurrentIndex(-1)

        except Exception as e:
            print(f"Error al cargar prefijos: {e}")

    def cargar_categorias(self):
        categorias = self.session.query(Categoria).filter_by(activo=True).all()
        for cat in categorias:
            self.cmb_categoria.addItem(cat.nombre, cat.id)

        self.cargar_prefijos_existentes()

    def cargar_datos_producto(self):
        prefijo_actual = self.producto.codigo.split('-')[0]

        self.cmb_codigo.setCurrentText(prefijo_actual)
        self.cmb_codigo.setEnabled(False)
        self.lbl_codigo_completo.setText('-' + self.producto.codigo.split('-')[1])

        self.actualizar_nombres_por_prefijo_edicion(prefijo_actual)
        self.cmb_nombre.setCurrentText(self.producto.nombre)

        self.txt_descripcion.setPlainText(self.producto.descripcion or "")

        index = self.cmb_categoria.findData(self.producto.categoria_id)
        if index >= 0:
            self.cmb_categoria.setCurrentIndex(index)

        for i, item_text in enumerate(UNIDADES_SUNAT):
            if item_text.startswith(self.producto.unidad_medida):
                self.cmb_unidad.setCurrentIndex(i)
                break

        if MovimientoStock:
            try:
                movimiento_existente = self.session.query(MovimientoStock).filter_by(producto_id=self.producto.id).first()
                if movimiento_existente:
                    self.cmb_unidad.setEnabled(False)
                    self.cmb_unidad.setToolTip("La unidad no se puede cambiar porque el producto ya tiene movimientos.")
            except Exception as e:
                print(f"Error al verificar movimientos: {e}")

        self.spn_stock_min.setValue(self.producto.stock_minimo)
        if self.producto.precio_venta:
            self.spn_precio_venta.setValue(self.producto.precio_venta)

        self.chk_tiene_lote.setChecked(self.producto.tiene_lote)
        self.chk_tiene_serie.setChecked(self.producto.tiene_serie)

        if self.producto.dias_vencimiento:
            self.chk_tiene_vencimiento.setChecked(True)
            self.spn_dias_vencimiento.setValue(self.producto.dias_vencimiento)

    def actualizar_siguiente_correlativo(self, prefijo):
        if self.cmb_codigo.isEnabled() == False:
            return

        prefijo = prefijo.strip().upper()

        if len(prefijo) != 5:
            self.lbl_codigo_completo.setText("-(inválido)")
            return

        try:
            codigo_completo = generar_codigo_completo(self.session, prefijo)
            sufijo = codigo_completo.split('-')[1]
            self.lbl_codigo_completo.setText(f"-{sufijo}")
        except Exception as e:
            print(f"Error al actualizar correlativo: {e}")
            self.lbl_codigo_completo.setText("-Error")

    def actualizar_nombres_por_prefijo(self, prefijo):
        if self.cmb_codigo.isEnabled() == False:
            return

        prefijo = prefijo.strip().upper()
        texto_actual = self.cmb_nombre.currentText()

        self.cmb_nombre.clear()

        placeholder = "Escriba un nombre nuevo"

        if len(prefijo) == 5:
            try:
                nombres = self.session.query(Producto.nombre).filter(
                    Producto.codigo.like(f"{prefijo}-%"),
                    Producto.activo == True
                ).order_by(Producto.nombre).all()

                lista_nombres = [nombre[0] for nombre in nombres]
                self.cmb_nombre.addItems(lista_nombres)

                if lista_nombres:
                    placeholder = "Escriba o seleccione un nombre"

            except Exception as e:
                print(f"Error al cargar nombres por prefijo: {e}")

        self.cmb_nombre.setCurrentText(texto_actual)
        if self.cmb_nombre.lineEdit():
            self.cmb_nombre.lineEdit().setPlaceholderText(placeholder)
        self.cmb_nombre.setCurrentIndex(-1 if texto_actual else 0)
        self.cmb_nombre.setCurrentText(texto_actual)

    def actualizar_nombres_por_prefijo_edicion(self, prefijo):
        self.cmb_nombre.clear()
        if len(prefijo) == 5:
            try:
                nombres = self.session.query(Producto.nombre).filter(
                    Producto.codigo.like(f"{prefijo}-%"),
                    Producto.activo == True
                ).order_by(Producto.nombre).all()
                self.cmb_nombre.addItems([nombre[0] for nombre in nombres])
            except Exception as e:
                print(f"Error al cargar nombres (edición): {e}")

    def guardar(self):
        codigo_prefijo = self.cmb_codigo.currentText().strip().upper()
        nombre = self.cmb_nombre.currentText().strip()
        categoria_id = self.cmb_categoria.currentData()
        unidad = self.cmb_unidad.currentText().split(' - ')[0]

        if len(codigo_prefijo) != 5:
            QMessageBox.warning(self, "Error", "El prefijo del código debe tener 5 caracteres")
            return

        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio")
            return

        if not categoria_id:
            QMessageBox.warning(self, "Error", "Debe seleccionar una categoría")
            return

        try:
            if not self.producto:
                codigo_completo = generar_codigo_completo(self.session, codigo_prefijo)

                existe = self.session.query(Producto).filter_by(codigo=codigo_completo).first()
                if existe:
                    QMessageBox.warning(self, "Error", f"El código {codigo_completo} ya existe. Intente de nuevo (el correlativo se actualizará).")
                    self.actualizar_siguiente_correlativo(codigo_prefijo)
                    return

                existe_nombre = self.session.query(Producto).filter(
                    Producto.nombre == nombre,
                    Producto.codigo.like(f"{codigo_prefijo}-%"),
                    Producto.activo == True
                ).first()
                if existe_nombre:
                        QMessageBox.warning(self, "Error", f"Ya existe un producto activo con el nombre '{nombre}' y el prefijo '{codigo_prefijo}'.")
                        return

                producto = Producto(
                    codigo=codigo_completo,
                    nombre=nombre,
                    descripcion=self.txt_descripcion.toPlainText(),
                    categoria_id=categoria_id,
                    unidad_medida=unidad,
                    stock_minimo=self.spn_stock_min.value(),
                    precio_venta=self.spn_precio_venta.value() if self.spn_precio_venta.value() > 0 else None,
                    tiene_lote=self.chk_tiene_lote.isChecked(),
                    tiene_serie=self.chk_tiene_serie.isChecked(),
                    dias_vencimiento=self.spn_dias_vencimiento.value() if self.chk_tiene_vencimiento.isChecked() else None
                )

                self.session.add(producto)
                self.session.flush()
                self.nuevo_producto_id = producto.id
                mensaje = "Producto creado exitosamente"
            else:
                self.producto = self.session.merge(self.producto)

                if self.producto.nombre != nombre:
                    existe_nombre = self.session.query(Producto).filter(
                        Producto.nombre == nombre,
                        Producto.codigo.like(f"{codigo_prefijo}-%"),
                        Producto.id != self.producto.id,
                        Producto.activo == True
                    ).first()
                    if existe_nombre:
                        QMessageBox.warning(self, "Error", f"Ya existe OTRO producto activo con el nombre '{nombre}' y el prefijo '{codigo_prefijo}'.")
                        return

                self.producto.nombre = nombre
                self.producto.descripcion = self.txt_descripcion.toPlainText()
                self.producto.categoria_id = categoria_id

                if self.cmb_unidad.isEnabled():
                    self.producto.unidad_medida = unidad

                self.producto.stock_minimo = self.spn_stock_min.value()
                self.producto.precio_venta = self.spn_precio_venta.value() if self.spn_precio_venta.value() > 0 else None
                self.producto.tiene_lote = self.chk_tiene_lote.isChecked()
                self.producto.tiene_serie = self.chk_tiene_serie.isChecked()
                self.producto.dias_vencimiento = self.spn_dias_vencimiento.value() if self.chk_tiene_vencimiento.isChecked() else None

                mensaje = "Producto actualizado exitosamente"

            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)

            self.producto_guardado.emit()
            self.session.close()
            self.accept()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")
            self.session.close()

    def reject(self):
        print("DEBUG: Diálogo de producto cancelado, cerrando sesión.")
        self.session.close()
        super().reject()


class ProductosWindow(BaseCRUDView):
    """Ventana principal de gestión de productos"""

    def __init__(self, user_info=None):
        self.user_info = user_info
        # BaseCRUDView constructor calls init_ui and load_data.
        # We need to override them because ProductosWindow has extra logic (category filter)
        super().__init__("Gestión de Productos", Producto, ProductoDialog)

    def init_ui(self):
        # We call super().init_ui() first to get the basic structure
        super().init_ui()

        # Customize title and buttons
        self.btn_nuevo.setText("+ Nuevo Producto")
        self.txt_buscar.setPlaceholderText("🔍 Buscar por código, nombre o categoría...")

        # Handle license restriction
        if self.user_info and self.user_info.get('licencia_vencida'):
            self.btn_nuevo.setEnabled(False)
            self.btn_nuevo.setToolTip("Licencia vencida - Solo consulta")

    def add_extra_filters(self, layout):
        """Overrides BaseCRUDView hook to add category filter."""
        self.cmb_categoria_filtro = SearchableComboBox()
        self.cmb_categoria_filtro.setStyleSheet("padding: 8px; min-width: 200px;")
        self.cargar_categorias_filtro()
        self.cmb_categoria_filtro.currentIndexChanged.connect(self.search_data)
        layout.addWidget(self.cmb_categoria_filtro, 1)

    def cargar_categorias_filtro(self):
        self.cmb_categoria_filtro.clear()
        self.cmb_categoria_filtro.addItem("Todas las categorías", None)
        try:
            # Use a fresh session or the current one
            categorias = self.session.query(Categoria).filter_by(activo=True).order_by(Categoria.nombre).all()
            for cat in categorias:
                self.cmb_categoria_filtro.addItem(cat.nombre, cat.id)
        except Exception as e:
            print(f"Error loading categories for filter: {e}")

    def setup_table_columns(self):
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "Código", "Nombre", "Categoría", "Unidad", "Stock Mín.",
            "Lote", "Serie", "Acciones"
        ])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(7, 150)

    def get_base_query(self):
        """Override to eager load category."""
        return self.session.query(Producto).options(
            joinedload(Producto.categoria)
        ).filter_by(activo=True)

    def apply_ordering(self, query):
        return query.order_by(Producto.nombre)

    def fill_row(self, row, prod):
        self.tabla.setItem(row, 0, QTableWidgetItem(prod.codigo))
        self.tabla.setItem(row, 1, QTableWidgetItem(prod.nombre))

        cat_nombre = prod.categoria.nombre if prod.categoria else "N/A"
        self.tabla.setItem(row, 2, QTableWidgetItem(cat_nombre))

        self.tabla.setItem(row, 3, QTableWidgetItem(prod.unidad_medida))
        self.tabla.setItem(row, 4, QTableWidgetItem(str(prod.stock_minimo)))

        check_lote = QTableWidgetItem("✓" if prod.tiene_lote else "✗")
        check_lote.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabla.setItem(row, 5, check_lote)

        check_serie = QTableWidgetItem("✓" if prod.tiene_serie else "✗")
        check_serie.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabla.setItem(row, 6, check_serie)

    def customize_buttons(self, layout, item, btn_edit, btn_delete):
        # License check
        if self.user_info and self.user_info.get('licencia_vencida'):
            btn_edit.setEnabled(False)
            btn_delete.setEnabled(False)

    def apply_search_filters(self, query, text):
        search_text = f"%{text}%"
        # We need to join Categoria again if not already joined?
        # get_base_query already does joinedload, but for filtering we might need explicit join if we filter by category name.
        # SQLAlchemy is smart enough usually.
        return query.join(Categoria).filter(
            or_(
                Producto.codigo.ilike(search_text),
                Producto.nombre.ilike(search_text),
                Categoria.nombre.ilike(search_text)
            )
        )

    def apply_extra_filters(self, query):
        categoria_id = self.cmb_categoria_filtro.currentData()
        if categoria_id:
            query = query.filter(Producto.categoria_id == categoria_id)
        return query

    def _open_dialog(self, item=None):
        """Override to connect the signal and handle dialog execution."""
        dialog = ProductoDialog(self, producto=item)

        # We connect the signal, but BaseCRUDView logic just calls exec().
        # In original code: dialog.producto_guardado.connect(self.recargar_datos)
        # recargar_datos reloaded products AND categories.

        dialog.producto_guardado.connect(self.recargar_datos_completos)

        dialog.exec()
        # Note: BaseCRUDView.create_item calls _open_dialog then load_data().
        # If dialog.exec() returns Accepted, base calls load_data().
        # But ProductoDialog emits a signal and might return Accepted too.
        # We should ensure double loading doesn't cause issues.
        # Actually, ProductoDialog.guardar calls accept().
        # So load_data will be called by BaseCRUDView.
        # But we also need to reload categories filter if a new category was added (less likely here, but good practice).
        # Original code reloaded categories.

    def recargar_datos_completos(self):
        """Slot to reload everything."""
        self.load_data()
        self.cargar_categorias_filtro()

    def create_item(self):
        # Override to match original method name/logic if needed, but BaseCRUDView.create_item is fine.
        # Except we need to handle the signal.
        # BaseCRUDView: create_item -> _open_dialog.
        super().create_item()

    def edit_item(self, item):
        super().edit_item(item)

    def delete_item(self, producto):
        # Override for specific validation logic (MovimientoStock check)

        if MovimientoStock is None:
            print("Advertencia: No se pudo importar 'MovimientoStock'.")
        else:
            try:
                movimiento_existente = self.session.query(MovimientoStock).filter_by(producto_id=producto.id).first()
                if movimiento_existente:
                    QMessageBox.warning(self, "Eliminación Bloqueada",
                        f"No se puede eliminar el producto '{producto.nombre}'.\n\n"
                        "Este producto ya tiene movimientos de Kardex registrados. "
                        "Desactivarlo podría causar inconsistencias en los reportes.")
                    return
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error de Validación",
                    f"No se pudo verificar la existencia de movimientos:\n{str(e)}")
                return

        # Call super to proceed with standard delete (confirmation + active=False)
        super().delete_item(producto)
        # Also reload categories if needed? Probably not.
        self.cargar_categorias_filtro()

# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    simulated_user_info = {
        'id': 1,
        'username': 'admin',
        'nombre_completo': 'Administrador',
        'rol': 'ADMINISTRADOR',
        'licencia_vencida': False
    }
    ventana = ProductosWindow(user_info=simulated_user_info)

    ventana.resize(1200, 700)
    ventana.show()

    sys.exit(app.exec())
