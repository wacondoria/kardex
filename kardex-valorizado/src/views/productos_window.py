"""
Gestión de Productos - Sistema Kardex Valorizado
Archivo: src/views/productos_window.py
(Versión corregida y unificada)
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                             QTextEdit, QCheckBox, QMessageBox, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QFileDialog)
# --- IMPORTACIONES CORREGIDAS ---
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QRegularExpression
from PyQt6.QtGui import QFont, QKeyEvent, QRegularExpressionValidator
# --- FIN CORRECCIÓN ---
import sys
from pathlib import Path
import re

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    print("Error: La librería 'openpyxl' no está instalada.")
    print("Por favor, instálela con: pip install openpyxl")
    sys.exit(1)

from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload # <--- IMPORTACIÓN AÑADIDA

sys.path.insert(0, str(Path(__file__).parent.parent))

# ===========================================================================
# MODIFICADO: Importar el modelo MovimientoStock (nombre correcto)
# ===========================================================================
try:
    from models.database_model import obtener_session, Producto, Categoria, MovimientoStock
except ImportError:
    # Fallback por si el modelo Movimiento aún no existe
    from models.database_model import obtener_session, Producto, Categoria
    MovimientoStock = None # Definir como None para que las comprobaciones fallen de forma segura
# ===========================================================================


# Lista de unidades movida fuera de la clase para ser reutilizada
UNIDADES_SUNAT = [
    "UND - Unidad",
    "KG - Kilogramo",
    "GR - Gramo",
    "LT - Litro",
    "ML - Mililitro",
    "M - Metro",
    "M2 - Metro cuadrado",
    "M3 - Metro cúbico",
    "CJ - Caja",
    "PQ - Paquete",
    "BOL - Bolsa",
    "SAC - Saco",
    "GLN - Galón",
    "DOC - Docena",
    "MIL - Millar"
]

# Función movida fuera de la clase para ser reutilizada
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
    
    # Señal para notificar a la ventana principal que se creó/editó un producto
    producto_guardado = pyqtSignal() 

    def __init__(self, parent=None, producto=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.producto = producto
        self.nuevo_producto_id = None # Para la integración con Compras
        self.init_ui()
        
        if producto:
            self.cargar_datos_producto()
    
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
        
        # --- CÓDIGO PREFIJO MEJORADO (COMBOBOX) ---
        codigo_layout = QHBoxLayout()
        self.cmb_codigo = QComboBox()
        self.cmb_codigo.setEditable(True)
        self.cmb_codigo.setPlaceholderText("Ej: TUBO0")
        self.cmb_codigo.setToolTip("Seleccione un prefijo existente o escriba uno nuevo (5 caracteres)")

        # --- CORRECCIÓN QT6: Usar QRegularExpression ---
        validator = QRegularExpressionValidator(QRegularExpression("[A-Z0-9]{5}")) # 5 caracteres alfanuméricos mayúsculas
        self.cmb_codigo.lineEdit().setValidator(validator)
        self.cmb_codigo.lineEdit().textChanged.connect(lambda text: self.cmb_codigo.lineEdit().setText(text.upper()))

        self.lbl_codigo_completo = QLabel("-000001")
        self.lbl_codigo_completo.setStyleSheet("color: #666; font-weight: bold;")

        codigo_layout.addWidget(self.cmb_codigo)
        codigo_layout.addWidget(self.lbl_codigo_completo)
        codigo_layout.addStretch()

        form_layout.addRow("Código (Prefijo):*", codigo_layout)
        # --- FIN MEJORA ---
        
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre del producto")
        form_layout.addRow("Nombre:*", self.txt_nombre)
        
        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(80)
        self.txt_descripcion.setPlaceholderText("Descripción detallada del producto")
        form_layout.addRow("Descripción:", self.txt_descripcion)
        
        self.cmb_categoria = QComboBox()
        self.cargar_categorias() # Esto ahora también carga los prefijos
        form_layout.addRow("Categoría:*", self.cmb_categoria)
        
        self.cmb_unidad = QComboBox()
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
        btn_cancelar.setStyleSheet("""
            QPushButton { background-color: #f1f3f4; color: #333; padding: 10px 30px;
                border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #e8eaed; }
        """)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("""
            QPushButton { background-color: #1a73e8; color: white; padding: 10px 30px;
                border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #1557b0; }
        """)
        btn_guardar.clicked.connect(self.guardar)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def cargar_prefijos_existentes(self):
        """Carga los prefijos de 5 caracteres únicos de la base de datos."""
        try:
            prefijos = self.session.query(
                func.substr(Producto.codigo, 1, 5)
            ).distinct().order_by(1).all()
            
            self.cmb_codigo.addItems([prefijo[0] for prefijo in prefijos if prefijo[0]])
            self.cmb_codigo.setCurrentIndex(-1) # Empezar sin selección
            
        except Exception as e:
            print(f"Error al cargar prefijos: {e}")
    
    def cargar_categorias(self):
        categorias = self.session.query(Categoria).filter_by(activo=True).all()
        for cat in categorias:
            self.cmb_categoria.addItem(cat.nombre, cat.id)
        
        self.cargar_prefijos_existentes() # <-- Llamada añadida
    
    def cargar_datos_producto(self):
        self.cmb_codigo.setCurrentText(self.producto.codigo.split('-')[0])
        self.cmb_codigo.setEnabled(False) # No se puede editar prefijo al editar
        self.lbl_codigo_completo.setText('-' + self.producto.codigo.split('-')[1])
        
        self.txt_nombre.setText(self.producto.nombre)
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
    
    def guardar(self):
        codigo_prefijo = self.cmb_codigo.currentText().strip().upper() # <-- CORREGIDO: Leer de cmb_codigo
        nombre = self.txt_nombre.text().strip()
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
                # --- LÓGICA DE CREACIÓN ---
                codigo_completo = generar_codigo_completo(self.session, codigo_prefijo)
                
                existe = self.session.query(Producto).filter_by(codigo=codigo_completo).first()
                if existe:
                    QMessageBox.warning(self, "Error", f"El código {codigo_completo} ya existe. Intente de nuevo (el correlativo se actualizará).")
                    return
                
                existe_nombre = self.session.query(Producto).filter(
                    Producto.nombre == nombre, 
                    Producto.codigo.like(f"{codigo_prefijo}-%")
                ).first()
                if existe_nombre:
                     QMessageBox.warning(self, "Error", f"Ya existe un producto con el nombre '{nombre}' y el prefijo '{codigo_prefijo}'.")
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
                self.session.flush() # Para obtener el ID
                self.nuevo_producto_id = producto.id # Guardar ID para ComprasWindow
                mensaje = "Producto creado exitosamente"
            else:
                # --- LÓGICA DE EDICIÓN (CORREGIDA) ---
                self.producto = self.session.merge(self.producto)
                
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
            
            self.producto_guardado.emit() # Emitir señal
            self.session.close() # Cerrar sesión
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")
            self.session.close() # Cerrar sesión también en error
    
    def reject(self):
        """Cierra la sesión de la base de datos al cancelar."""
        print("DEBUG: Diálogo de producto cancelado, cerrando sesión.")
        self.session.close()
        super().reject()


class ProductosWindow(QWidget):
    """Ventana principal de gestión de productos"""
    
    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.init_ui()
        self.cargar_productos()
    
    def init_ui(self):
        self.setWindowTitle("Gestión de Productos")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("📦 Gestión de Productos")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        btn_nuevo = QPushButton("➕ Nuevo Producto")
        btn_nuevo.setStyleSheet("""
            QPushButton { background-color: #1a73e8; color: white; padding: 10px 20px;
                border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #1557b0; }
        """)
        btn_nuevo.clicked.connect(self.nuevo_producto)
        
        secondary_btn_style = """
            QPushButton {
                background-color: #1D6F42; /* Excel Green */
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #185C37; }
        """
        
        btn_plantilla = QPushButton("📄 Generar Plantilla")
        btn_plantilla.setStyleSheet(secondary_btn_style)
        btn_plantilla.setToolTip("Generar plantilla Excel para importación masiva")
        btn_plantilla.clicked.connect(self.generar_plantilla)

        btn_importar = QPushButton("📥 Importar Excel")
        btn_importar.setStyleSheet(secondary_btn_style.replace("#1D6F42", "#107C41").replace("#185C37", "#0D6534"))
        btn_importar.setToolTip("Importar productos desde plantilla Excel")
        btn_importar.clicked.connect(self.importar_productos)

        if self.user_info and self.user_info.get('licencia_vencida'):
            btn_nuevo.setEnabled(False)
            btn_plantilla.setEnabled(False)
            btn_importar.setEnabled(False)
            btn_nuevo.setToolTip("Licencia vencida - Solo consulta")
            btn_plantilla.setToolTip("Licencia vencida - Solo consulta")
            btn_importar.setToolTip("Licencia vencida - Solo consulta")

        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_plantilla)
        header_layout.addWidget(btn_importar)
        header_layout.addWidget(btn_nuevo)
        
        # Búsqueda
        search_layout = QHBoxLayout()
        
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar por código, nombre o categoría...")
        self.txt_buscar.setStyleSheet("""
            QLineEdit { padding: 10px; border: 2px solid #ddd; border-radius: 5px; font-size: 12px; }
            QLineEdit:focus { border: 2px solid #1a73e8; }
        """)
        self.txt_buscar.textChanged.connect(self.buscar_productos)
        
        self.cmb_categoria_filtro = QComboBox()
        self.cmb_categoria_filtro.setStyleSheet("padding: 8px; min-width: 200px;")
        self.cargar_categorias_filtro()
        self.cmb_categoria_filtro.currentIndexChanged.connect(self.buscar_productos)
        
        search_layout.addWidget(self.txt_buscar, 3)
        search_layout.addWidget(self.cmb_categoria_filtro, 1)
        
        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "Código", "Nombre", "Categoría", "Unidad", "Stock Mín.", 
            "Lote", "Serie", "Acciones"
        ])
        
        self.tabla.setStyleSheet("""
            QTableWidget { border: 1px solid #ddd; border-radius: 5px; background-color: white; }
            QHeaderView::section { background-color: #f1f3f4; padding: 10px;
                border: none; font-weight: bold; }
        """)
        
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(7, 150)
        
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addLayout(header_layout)
        layout.addLayout(search_layout)
        layout.addWidget(self.tabla)
        
        self.setLayout(layout)
    
    def cargar_categorias_filtro(self):
        self.cmb_categoria_filtro.clear()
        self.cmb_categoria_filtro.addItem("Todas las categorías", None)
        categorias = self.session.query(Categoria).filter_by(activo=True).order_by(Categoria.nombre).all()
        for cat in categorias:
            self.cmb_categoria_filtro.addItem(cat.nombre, cat.id)
            
    def cargar_productos(self):
        try:
            self.session.expire_all()
            productos = self.session.query(Producto).options(
                joinedload(Producto.categoria)
            ).filter_by(activo=True).order_by(Producto.nombre).all()
            self.mostrar_productos(productos)
        except Exception as e:
            print(f"Error al recargar productos: {e}")
            self.session.rollback()
            self.session = obtener_session() 
            productos = self.session.query(Producto).options(
                joinedload(Producto.categoria)
            ).filter_by(activo=True).order_by(Producto.nombre).all()
            self.mostrar_productos(productos)
    
    def mostrar_productos(self, productos):
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(productos))
        
        for row, prod in enumerate(productos):
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
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 5, 5, 5)
            btn_layout.setSpacing(5)
            
            btn_editar = QPushButton("Editar")
            btn_editar.setStyleSheet("""
                QPushButton { background-color: #34a853; color: white; padding: 5px 10px;
                    border: none; border-radius: 3px; }
                QPushButton:hover { background-color: #2d8e47; }
            """)
            btn_editar.clicked.connect(lambda checked, p=prod: self.editar_producto(p))
            
            btn_eliminar = QPushButton("Eliminar")
            btn_eliminar.setStyleSheet("""
                QPushButton { background-color: #ea4335; color: white; padding: 5px 10px;
                    border: none; border-radius: 3px; }
                QPushButton:hover { background-color: #c5221f; }
            """)
            btn_eliminar.clicked.connect(lambda checked, p=prod: self.eliminar_producto(p))
            
            if self.user_info and self.user_info.get('licencia_vencida'):
                btn_editar.setEnabled(False)
                btn_eliminar.setEnabled(False)

            btn_layout.addWidget(btn_editar)
            btn_layout.addWidget(btn_eliminar)
            btn_layout.addStretch()
            btn_widget.setLayout(btn_layout)
            
            self.tabla.setCellWidget(row, 7, btn_widget)
    
    def buscar_productos(self):
        texto = self.txt_buscar.text().strip()
        categoria_id = self.cmb_categoria_filtro.currentData()
        
        try:
            query = self.session.query(Producto).options(
                joinedload(Producto.categoria)
            ).filter(Producto.activo == True)
            
            if categoria_id:
                query = query.filter_by(categoria_id=categoria_id)
            
            if texto:
                search_text = f"%{texto}%"
                query = query.join(Categoria).filter(
                    or_(
                        Producto.codigo.ilike(search_text),
                        Producto.nombre.ilike(search_text),
                        Categoria.nombre.ilike(search_text) 
                    )
                )
            
            productos = query.order_by(Producto.nombre).all()
            self.mostrar_productos(productos)
            
        except Exception as e:
            QMessageBox.critical(self, "Error de Búsqueda", f"Error al consultar la base de datos:\n{e}")

    
    def nuevo_producto(self):
        dialog = ProductoDialog(self)
        dialog.producto_guardado.connect(self.recargar_datos)
        dialog.exec()
    
    def editar_producto(self, producto):
        dialog = ProductoDialog(self, producto)
        dialog.producto_guardado.connect(self.recargar_datos)
        dialog.exec()

    def recargar_datos(self):
        """Slot para recargar productos y categorías."""
        print("DEBUG: Señal recibida, recargando productos y categorías...")
        self.cargar_productos()
        self.cargar_categorias_filtro()
    
    def eliminar_producto(self, producto):
        """Elimina (desactiva) un producto, validando movimientos primero"""
        
        if MovimientoStock is None:
            print("Advertencia: No se pudo importar 'MovimientoStock'. "
                  "Se omitirá la validación de movimientos al eliminar.")
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

        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Está seguro de eliminar el producto:\n{producto.codigo} - {producto.nombre}?\n\n"
            "El producto se desactivará pero se mantendrá en el historial.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                producto_a_eliminar = self.session.merge(producto)
                producto_a_eliminar.activo = False
                self.session.commit()
                QMessageBox.information(self, "Éxito", "Producto eliminado correctamente")
                self.cargar_productos()
                self.cargar_categorias_filtro() # Recargar categorías también
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error al eliminar:\n{str(e)}")


    # --- MÉTODOS PARA IMPORTACIÓN/PLANTILLA (Estilo Proveedores) ---

    def generar_plantilla(self):
        """Genera una plantilla Excel para la importación masiva"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Plantilla",
            "plantilla_productos.xlsx",
            "Archivos de Excel (*.xlsx)"
        )
        
        if not path:
            return

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Productos"

            headers = [
                "CODIGO_PREFIJO", "NOMBRE", "DESCRIPCION", "CATEGORIA", "UNIDAD_MEDIDA",
                "STOCK_MINIMO", "PRECIO_VENTA", "MANEJA_LOTE", "MANEJA_SERIE",
                "TIENE_VENCIMIENTO", "DIAS_VENCIMIENTO"
            ]
            ws.append(headers)

            header_font = Font(bold=True, color="FFFFFF")
            header_fill = "FF1D6F42"
            header_align = Alignment(horizontal="center")

            for cell in ws[1]:
                cell.font = header_font
                cell.fill = PatternFill(start_color=header_fill, end_color=header_fill, fill_type="solid")
                cell.alignment = header_align
            
            dv_sino = DataValidation(type="list", formula1='"SI,NO"', allow_blank=True)
            ws.add_data_validation(dv_sino)
            dv_sino.add('H2:J1000')

            unidades_codigos = [u.split(' - ')[0] for u in UNIDADES_SUNAT]
            dv_unidad = DataValidation(type="list", formula1=f'"{",".join(unidades_codigos)}"', allow_blank=False)
            ws.add_data_validation(dv_unidad)
            dv_unidad.add('E2:E1000')
            
            # Usar la sesión de la ventana principal para esto
            categorias = self.session.query(Categoria).filter_by(activo=True).all()
            cat_nombres = [c.nombre.replace('"', "''") for c in categorias]
            if cat_nombres:
                dv_cat = DataValidation(type="list", formula1=f'"{",".join(cat_nombres)}"', allow_blank=False)
                ws.add_data_validation(dv_cat)
                dv_cat.add('D2:D1000')

            ws.column_dimensions['A'].width = 18
            ws.column_dimensions['B'].width = 40
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 25
            ws.column_dimensions['E'].width = 18
            for col in ['F', 'G', 'H', 'I', 'J', 'K']:
                ws.column_dimensions[col].width = 18

            ws_inst = wb.create_sheet(title="Instrucciones")
            ws_inst.append(["Columna", "Descripción", "Obligatorio"])
            ws_inst.append(["CODIGO_PREFIJO", "Prefijo de 5 caracteres para el código (Ej: TUBO0). El correlativo se generará automáticamente.", "Sí"])
            ws_inst.append(["NOMBRE", "Nombre del producto.", "Sí"])
            ws_inst.append(["DESCRIPCION", "Descripción detallada (opcional).", "No"])
            ws_inst.append(["CATEGORIA", "Nombre exacto de una categoría ya existente.", "Sí"])
            ws_inst.append(["UNIDAD_MEDIDA", "Código de unidad de medida (Ej: UND, KG, M).", "Sí"])
            ws_inst.append(["STOCK_MINIMO", "Valor numérico (opcional, defecto 0).", "No"])
            ws_inst.append(["PRECIO_VENTA", "Valor numérico (opcional, defecto 0).", "No"])
            ws_inst.append(["MANEJA_LOTE", "Escribir 'SI' o 'NO' (opcional, defecto NO).", "No"])
            ws_inst.append(["MANEJA_SERIE", "Escribir 'SI' o 'NO' (opcional, defecto NO).", "No"])
            ws_inst.append(["TIENE_VENCIMIENTO", "Escribir 'SI' o 'NO' (opcional, defecto NO).", "No"])
            ws_inst.append(["DIAS_VENCIMIENTO", "Número de días (solo si la columna anterior es 'SI').", "No"])

            wb.save(path)
            QMessageBox.information(self, "Éxito", f"Plantilla guardada exitosamente en:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la plantilla:\n{str(e)}")

    def importar_productos(self):
        """Importa productos desde un archivo Excel (Estilo Openpyxl)"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Plantilla",
            "",
            "Archivos de Excel (*.xlsx *.xls)"
        )
        
        if not path:
            return

        try:
            wb = load_workbook(path, data_only=True)
            
            if "Productos" not in wb.sheetnames:
                QMessageBox.critical(self, "Error de Hoja",
                    "No se encontró la hoja llamada 'Productos' en el archivo.")
                return
                
            ws = wb["Productos"]

            # 1. Validar encabezados
            expected_headers = [
                "CODIGO_PREFIJO", "NOMBRE", "DESCRIPCION", "CATEGORIA", "UNIDAD_MEDIDA",
                "STOCK_MINIMO", "PRECIO_VENTA", "MANEJA_LOTE", "MANEJA_SERIE",
                "TIENE_VENCIMIENTO", "DIAS_VENCIMIENTO"
            ]
            actual_headers = [str(cell.value).upper().strip() for cell in ws[1]]
            actual_headers = actual_headers[:len(expected_headers)]

            if actual_headers != expected_headers:
                QMessageBox.critical(self, "Error de Formato",
                    f"Los encabezados del Excel no son correctos.\n"
                    f"Se esperaba: {', '.join(expected_headers)}\n"
                    f"Se encontró: {', '.join(actual_headers)}")
                return

            # 2. Leer datos del Excel
            productos_a_crear = []
            errores_lectura = []
            
            categorias_db = self.session.query(Categoria).filter_by(activo=True).all()
            cat_map = {cat.nombre.upper(): cat.id for cat in categorias_db}
            unidades_validas = [u.split(' - ')[0] for u in UNIDADES_SUNAT]
            nombres_prefijos_excel = set()

            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if all(c is None for c in row):
                    break
                
                try:
                    codigo_prefijo = str(row[0]).strip().upper() if row[0] else ""
                    nombre = str(row[1]).strip() if row[1] else ""
                    descripcion = str(row[2]).strip() if row[2] else None
                    categoria_nombre = str(row[3]).strip().upper() if row[3] else ""
                    unidad = str(row[4]).strip().upper() if row[4] else ""
                    stock_min_str = str(row[5]).strip() if row[5] else "0"
                    precio_venta_str = str(row[6]).strip() if row[6] else "0"
                    maneja_lote_str = str(row[7]).strip().upper() if row[7] else "NO"
                    maneja_serie_str = str(row[8]).strip().upper() if row[8] else "NO"
                    tiene_venc_str = str(row[9]).strip().upper() if row[9] else "NO"
                    dias_venc_str = str(row[10]).strip() if row[10] else "0"

                    if not codigo_prefijo and not nombre:
                        continue 

                    if len(codigo_prefijo) != 5:
                        raise ValueError(f"Código prefijo debe tener 5 caracteres. Se recibió: '{codigo_prefijo}'")
                    if not nombre:
                        raise ValueError("El Nombre es obligatorio.")
                    
                    categoria_id = cat_map.get(categoria_nombre)
                    if not categoria_id:
                        raise ValueError(f"Categoría '{row[3]}' no encontrada o inactiva.")
                    
                    if unidad not in unidades_validas:
                        raise ValueError(f"Unidad_Medida '{unidad}' no es válida.")

                    try: stock_min = float(stock_min_str)
                    except ValueError: raise ValueError(f"Stock Mínimo '{stock_min_str}' no es un número.")
                    
                    try: precio_venta = float(precio_venta_str)
                    except ValueError: raise ValueError(f"Precio Venta '{precio_venta_str}' no es un número.")

                    tiene_lote = maneja_lote_str == "SI"
                    tiene_serie = maneja_serie_str == "SI"
                    tiene_vencimiento = tiene_venc_str == "SI"
                    
                    dias_vencimiento = None
                    if tiene_vencimiento:
                        try: dias_vencimiento = int(dias_venc_str)
                        except ValueError: raise ValueError(f"Dias Vencimiento '{dias_venc_str}' no es un número entero.")
                        if dias_vencimiento <= 0:
                            tiene_vencimiento = False
                            dias_vencimiento = None
                    
                    if (codigo_prefijo, nombre) in nombres_prefijos_excel:
                        raise ValueError(f"Duplicado en Excel: Prefijo '{codigo_prefijo}' y Nombre '{nombre}' repetidos.")
                    nombres_prefijos_excel.add((codigo_prefijo, nombre))

                    productos_a_crear.append({
                        "prefijo": codigo_prefijo, "nombre": nombre, "desc": descripcion,
                        "cat_id": categoria_id, "unidad": unidad, "stock_min": stock_min,
                        "precio": precio_venta, "lote": tiene_lote, "serie": tiene_serie,
                        "dias_venc": dias_vencimiento, "fila": row_idx
                    })

                except Exception as e:
                    errores_lectura.append(f"Fila {row_idx}: {str(e)}")
            
            if not productos_a_crear and not errores_lectura:
                 QMessageBox.warning(self, "Archivo Vacío", "No se encontraron datos de productos válidos en el archivo.")
                 return

            # 3. Procesar datos (Solo Creación, optimizado)
            creados = 0
            correlativos_map = {} 
            nombres_prefijos_db = {
                (p.codigo.split('-')[0], p.nombre) 
                for p in self.session.query(Producto).filter_by(activo=True).all()
            }

            for data in productos_a_crear:
                try:
                    prefijo = data['prefijo']
                    nombre = data['nombre']
                    
                    if (prefijo, nombre) in nombres_prefijos_db:
                        raise ValueError(f"Ya existe un producto con Prefijo '{prefijo}' y Nombre '{nombre}' en la BD.")

                    if prefijo not in correlativos_map:
                        ultimo = self.session.query(Producto).filter(
                            Producto.codigo.like(f"{prefijo}-%")
                        ).order_by(Producto.codigo.desc()).first()
                        correlativos_map[prefijo] = int(ultimo.codigo.split('-')[1]) if ultimo else 0
                    
                    correlativos_map[prefijo] += 1
                    numero = correlativos_map[prefijo]
                    codigo_completo = f"{prefijo}-{numero:06d}"

                    producto = Producto(
                        codigo=codigo_completo,
                        nombre=data['nombre'],
                        descripcion=data['desc'],
                        categoria_id=data['cat_id'],
                        unidad_medida=data['unidad'],
                        stock_minimo=data['stock_min'],
                        precio_venta=data['precio'] if data['precio'] > 0 else None,
                        tiene_lote=data['lote'],
                        tiene_serie=data['serie'],
                        dias_vencimiento=data['dias_venc']
                    )
                    
                    self.session.add(producto)
                    creados += 1
                
                except Exception as e:
                    errores_lectura.append(f"Fila {data['fila']} (Procesando): {str(e)}")

            # 4. Commit y Reporte
            self.session.commit()
            
            mensaje = f"Importación completada.\n\n" \
                      f"✅ Productos nuevos creados: {creados}\n"
            
            if errores_lectura:
                mensaje += f"\n⚠️ Se encontraron {len(errores_lectura)} errores que fueron omitidos:\n"
                mensaje += "\n".join(errores_lectura[:10])
                if len(errores_lectura) > 10:
                    mensaje += f"\n... y {len(errores_lectura) - 10} más."
                QMessageBox.warning(self, "Importación con Errores", mensaje)
            else:
                QMessageBox.information(self, "Importación Exitosa", mensaje)

            self.cargar_productos()
            self.cargar_categorias_filtro()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error Crítico", f"Ocurrió un error inesperado al importar:\n{str(e)}")

# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # --- PRUEBA CON user_info simulado ---
    simulated_user_info = {
        'id': 1,
        'username': 'admin',
        'nombre_completo': 'Administrador',
        'rol': 'ADMINISTRADOR',
        'licencia_vencida': False 
    }
    ventana = ProductosWindow(user_info=simulated_user_info)
    # --- FIN PRUEBA ---
    
    ventana.resize(1200, 700)
    ventana.show()
    
    sys.exit(app.exec())