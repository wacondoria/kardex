"""
Gestión de Compras - Sistema Kardex Valorizado
Archivo: src/views/compras_window.py
(Versión corregida y unificada)
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox,
                             QTextEdit, QCheckBox, QMessageBox, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QSpinBox,
                             QSizePolicy, QFileDialog)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QEvent
from PyQt6.QtGui import QFont, QKeyEvent
import sys
import calendar
import shutil
from pathlib import Path
try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    print("Error: La librería 'openpyxl' no está instalada.")
    print("Por favor, instálela con: pip install openpyxl")
    sys.exit(1)
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import func, extract

sys.path.insert(0, str(Path(__file__).parent.parent))

# --- IMPORTACIÓN DE DIÁLOGOS MAESTROS ---
from .productos_window import ProductoDialog
try:
    from .proveedores_window import ProveedorDialog
except ImportError:
    print("ADVERTENCIA: No se encontró 'proveedores_window.py'. El botón 'Nuevo Proveedor' no funcionará.")
    ProveedorDialog = None
# --- FIN DE IMPORTACIONES ---

from models.database_model import (obtener_session, Compra, CompraDetalle,
                                   Proveedor, Producto, Almacen, Empresa,
                                   TipoCambio, TipoDocumento, Moneda,
                                   MovimientoStock, TipoMovimiento)
from utils.widgets import UppercaseValidator, SearchableComboBox
from utils.app_context import app_context
from utils.validation import verificar_estado_anio, AnioCerradoError

# ============================================
# CLASES AUXILIARES (para seleccionar texto)
# ============================================

class SelectAllLineEdit(QLineEdit):
    """Un QLineEdit que selecciona todo su texto al recibir el foco."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(UppercaseValidator())

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()

class SelectAllSpinBox(QDoubleSpinBox):
    """Un QDoubleSpinBox que selecciona todo su texto al recibir el foco."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.selectAll)

# ============================================
# DIÁLOGO DE CREAR/EDITAR COMPRA
# ============================================

class CompraDialog(QDialog):
    """Diálogo para registrar y editar compras"""

    def __init__(self, parent=None, user_info=None, compra_a_editar=None, detalles_originales=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.user_info = user_info
        self.compra_original = compra_a_editar
        self.detalles_originales_obj = detalles_originales
        self.detalles_compra = []
        self.lista_completa_productos = []

        self.init_ui()
        self.cargar_datos_iniciales()

        if self.compra_original:
            self.cargar_datos_para_edicion()

    def init_ui(self):
        self.setWindowTitle("Registrar Compra")
        self.setMinimumSize(1000, 700)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Título
        titulo = QLabel("🛒 Nueva Compra")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)

        # === DATOS DE LA COMPRA ===
        grupo_compra = QGroupBox("Datos de la Compra")
        form_compra = QFormLayout()
        form_compra.setSpacing(10)

        # Proveedor (CON BOTÓN +)
        proveedor_layout = QHBoxLayout()
        self.cmb_proveedor = SearchableComboBox()
        self.cmb_proveedor.setMinimumWidth(400)
        self.cmb_proveedor.currentIndexChanged.connect(self.proveedor_seleccionado)

        self.btn_nuevo_proveedor = QPushButton("+")
        self.btn_nuevo_proveedor.setToolTip("Crear nuevo proveedor")
        self.btn_nuevo_proveedor.setFixedSize(30, 30)
        self.btn_nuevo_proveedor.setStyleSheet("background-color: #34a853; color: white; font-weight: bold; border-radius: 15px;")
        self.btn_nuevo_proveedor.clicked.connect(self.crear_nuevo_proveedor)

        self.lbl_proveedor_info = QLabel()
        self.lbl_proveedor_info.setStyleSheet("color: #666; font-size: 10px;")

        proveedor_layout.addWidget(self.cmb_proveedor)
        proveedor_layout.addWidget(self.btn_nuevo_proveedor)
        proveedor_layout.addWidget(self.lbl_proveedor_info)
        proveedor_layout.addStretch()

        form_compra.addRow("Proveedor:*", proveedor_layout)

        # Fecha, Tipo Doc, Número
        fila1 = QHBoxLayout()

        self.date_fecha = QDateEdit()
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.setDate(QDate.currentDate())
        self.date_fecha.setDisplayFormat("dd/MM/yyyy")
        self.date_fecha.setToolTip("Fecha de Emisión del Documento (usada para el Kardex)")
        self.date_fecha.dateChanged.connect(self.fecha_cambiada)
        self.date_fecha.dateChanged.connect(self.sincronizar_fecha_contable)

        self.date_fecha_contable = QDateEdit()
        self.date_fecha_contable.setCalendarPopup(True)
        self.date_fecha_contable.setDate(QDate.currentDate())
        self.date_fecha_contable.setDisplayFormat("dd/MM/yyyy")
        self.date_fecha_contable.setToolTip("Fecha de registro para el Periodo Contable (para conciliación)")

        self.cmb_tipo_doc = QComboBox()
        self.cmb_tipo_doc.addItem("FACTURA", TipoDocumento.FACTURA.value)
        self.cmb_tipo_doc.addItem("BOLETA", TipoDocumento.BOLETA.value)

        self.txt_serie_doc = SelectAllLineEdit()
        self.txt_serie_doc.setPlaceholderText("F001")
        self.txt_serie_doc.setMaximumWidth(60)

        self.txt_numero_doc = SelectAllLineEdit()
        self.txt_numero_doc.setPlaceholderText("00001234")
        self.txt_numero_doc.editingFinished.connect(self.formatear_numero_documento)

        fila1.addWidget(QLabel("Fecha Emisión:"))
        fila1.addWidget(self.date_fecha)
        fila1.addWidget(QLabel("Fecha Contable:"))
        fila1.addWidget(self.date_fecha_contable)
        fila1.addSpacing(10)
        fila1.addWidget(QLabel("Tipo:"))
        fila1.addWidget(self.cmb_tipo_doc)
        fila1.addWidget(QLabel("Número:"))
        fila1.addWidget(self.txt_serie_doc)
        fila1.addWidget(QLabel("-"))
        fila1.addWidget(self.txt_numero_doc)
        fila1.addStretch()

        form_compra.addRow("", fila1)

        # Moneda y Tipo de Cambio
        fila2 = QHBoxLayout()

        self.cmb_moneda = QComboBox()
        self.cmb_moneda.addItem("SOLES (S/)", Moneda.SOLES.value)
        self.cmb_moneda.addItem("DÓLARES ($)", Moneda.DOLARES.value)
        self.cmb_moneda.currentIndexChanged.connect(self.moneda_cambiada)

        self.spn_tipo_cambio = QDoubleSpinBox()
        self.spn_tipo_cambio.setRange(0.001, 99.999)
        self.spn_tipo_cambio.setDecimals(3)
        self.spn_tipo_cambio.setValue(1.000)
        self.spn_tipo_cambio.setEnabled(False)

        self.lbl_tc_info = QLabel("Tipo cambio VENTA")
        self.lbl_tc_info.setStyleSheet("color: #666; font-size: 10px;")

        fila2.addWidget(QLabel("Moneda:"))
        fila2.addWidget(self.cmb_moneda)
        fila2.addWidget(QLabel("Tipo Cambio:"))
        fila2.addWidget(self.spn_tipo_cambio)
        fila2.addWidget(self.lbl_tc_info)
        fila2.addStretch()

        form_compra.addRow("", fila2)

        # IGV
        self.chk_incluye_igv = QCheckBox("Los precios INCLUYEN IGV (18%)")
        self.chk_incluye_igv.setStyleSheet("font-weight: bold; color: #ea4335;")
        self.chk_incluye_igv.toggled.connect(self.recalcular_totales)
        form_compra.addRow("", self.chk_incluye_igv)

        grupo_compra.setLayout(form_compra)
        layout.addWidget(grupo_compra)

        # === PRODUCTOS (CON BOTÓN +) ===
        grupo_productos = QGroupBox("Productos")
        productos_layout = QVBoxLayout()

        # Selector de producto
        selector_layout = QHBoxLayout()

        self.cmb_producto = SearchableComboBox()
        self.cmb_producto.setMinimumWidth(300)
        self.cmb_producto.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self.btn_nuevo_producto = QPushButton("+")
        self.btn_nuevo_producto.setToolTip("Crear nuevo producto")
        self.btn_nuevo_producto.setFixedSize(30, 30)
        self.btn_nuevo_producto.setStyleSheet("background-color: #34a853; color: white; font-weight: bold; border-radius: 15px;")
        self.btn_nuevo_producto.clicked.connect(self.crear_nuevo_producto)

        self.cmb_almacen = SearchableComboBox()

        self.spn_cantidad = SelectAllSpinBox()
        self.spn_cantidad.setRange(0.00, 999999)
        self.spn_cantidad.setDecimals(2)
        self.spn_cantidad.setValue(1.00)

        self.spn_precio = SelectAllSpinBox()
        self.spn_precio.setRange(0.00, 999999.99)
        self.spn_precio.setDecimals(2)

        self.btn_agregar = QPushButton("+ Agregar")
        self.btn_agregar.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.btn_agregar.clicked.connect(self.agregar_producto)

        # Instalar filtros de eventos
        self.cmb_producto.installEventFilter(self)
        self.cmb_almacen.installEventFilter(self)
        self.spn_cantidad.installEventFilter(self)
        self.spn_precio.installEventFilter(self)
        self.btn_agregar.installEventFilter(self)

        selector_layout.addWidget(QLabel("Producto:"))
        selector_layout.addWidget(self.cmb_producto, 2)
        selector_layout.addWidget(self.btn_nuevo_producto) # <-- Botón añadido
        selector_layout.addWidget(QLabel("Almacén:"))
        selector_layout.addWidget(self.cmb_almacen, 1)
        selector_layout.addWidget(QLabel("Cant:"))
        selector_layout.addWidget(self.spn_cantidad)
        selector_layout.addWidget(QLabel("Precio:"))
        selector_layout.addWidget(self.spn_precio)
        selector_layout.addWidget(self.btn_agregar)
        productos_layout.addLayout(selector_layout)

        # Tabla de productos
        self.tabla_productos = QTableWidget()
        self.tabla_productos.setColumnCount(6)
        self.tabla_productos.setHorizontalHeaderLabels([
            "Producto", "Almacén", "Cantidad", "Precio Unit.", "Subtotal", "Acción"
        ])

        header = self.tabla_productos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla_productos.setColumnWidth(5, 80)

        productos_layout.addWidget(self.tabla_productos)

        grupo_productos.setLayout(productos_layout)
        layout.addWidget(grupo_productos)

        # === TOTALES Y COSTOS ADICIONALES ===
        totales_layout = QHBoxLayout()

        # Costos adicionales
        grupo_costos = QGroupBox("Costos Adicionales")
        costos_layout = QFormLayout()

        self.spn_costo_adicional = QDoubleSpinBox()
        self.spn_costo_adicional.setRange(0, 99999.99)
        self.spn_costo_adicional.setDecimals(2)
        self.spn_costo_adicional.valueChanged.connect(self.recalcular_totales)

        self.txt_desc_costo = SelectAllLineEdit()
        self.txt_desc_costo.setPlaceholderText("Ej: Flete, seguro, etc.")

        costos_layout.addRow("Monto:", self.spn_costo_adicional)
        costos_layout.addRow("Descripción:", self.txt_desc_costo)

        grupo_costos.setLayout(costos_layout)
        totales_layout.addWidget(grupo_costos)

        # Resumen
        grupo_resumen = QGroupBox("Resumen")
        resumen_layout = QFormLayout()

        self.lbl_subtotal = QLabel("S/ 0.00")
        self.lbl_subtotal.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.lbl_igv = QLabel("S/ 0.00")
        self.lbl_igv.setStyleSheet("font-size: 14px;")

        self.lbl_total = QLabel("S/ 0.00")
        self.lbl_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a73e8;")

        resumen_layout.addRow("Subtotal (sin IGV):", self.lbl_subtotal)
        resumen_layout.addRow("IGV (18%):", self.lbl_igv)
        resumen_layout.addRow("TOTAL:", self.lbl_total)

        grupo_resumen.setLayout(resumen_layout)
        totales_layout.addWidget(grupo_resumen)

        layout.addLayout(totales_layout)

        # Observaciones
        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setMaximumHeight(60)
        self.txt_observaciones.setPlaceholderText("Observaciones adicionales...")
        layout.addWidget(QLabel("Observaciones:"))
        layout.addWidget(self.txt_observaciones)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f4;
                padding: 10px 30px;
                border-radius: 5px;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar Compra")
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.btn_guardar.clicked.connect(self.guardar_compra)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def recalcular_kardex_posterior(self, producto_almacen_afectados, fecha_referencia):
        """
        Recalcula los saldos y costos del Kardex para productos/almacenes específicos
        a partir de una fecha dada. ASUME COSTO PROMEDIO PONDERADO.
        """
        print(f"DEBUG: Iniciando recálculo de Kardex para {len(producto_almacen_afectados)} pares desde {fecha_referencia}")
        DOS_DECIMALES = Decimal('0.01')
        SEIS_DECIMALES = Decimal('0.000001')

        for prod_id, alm_id in producto_almacen_afectados:
            print(f"DEBUG: Recalculando para Producto ID: {prod_id}, Almacén ID: {alm_id}")

            mov_anterior = self.session.query(MovimientoStock).filter(
                MovimientoStock.producto_id == prod_id,
                MovimientoStock.almacen_id == alm_id,
                MovimientoStock.fecha_documento < fecha_referencia
            ).order_by(MovimientoStock.fecha_documento.desc(), MovimientoStock.id.desc()).first()

            saldo_cant_actual = Decimal(str(mov_anterior.saldo_cantidad)) if mov_anterior else Decimal('0')
            saldo_costo_actual = Decimal(str(mov_anterior.saldo_costo_total)) if mov_anterior else Decimal('0')
            print(f"DEBUG: Saldos iniciales - Cant: {saldo_cant_actual}, Costo Total: {saldo_costo_actual}")

            movimientos_a_recalcular = self.session.query(MovimientoStock).filter(
                MovimientoStock.producto_id == prod_id,
                MovimientoStock.almacen_id == alm_id,
                MovimientoStock.fecha_documento >= fecha_referencia
            ).order_by(MovimientoStock.fecha_documento.asc(), MovimientoStock.id.asc()).all()

            if not movimientos_a_recalcular:
                print(f"DEBUG: No hay movimientos posteriores para recalcular.")
                continue

            for mov in movimientos_a_recalcular:
                cant_entrada = Decimal(str(mov.cantidad_entrada))
                cant_salida = Decimal(str(mov.cantidad_salida))
                costo_total_movimiento = Decimal(str(mov.costo_total))

                costo_promedio_anterior = Decimal('0')
                if saldo_cant_actual > 0:
                    costo_promedio_anterior = (saldo_costo_actual / saldo_cant_actual).quantize(SEIS_DECIMALES, rounding=ROUND_HALF_UP)

                if cant_salida > 0:
                    costo_unitario_salida = costo_promedio_anterior
                    costo_total_salida = (cant_salida * costo_unitario_salida).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

                    mov.costo_unitario = float(costo_unitario_salida)
                    mov.costo_total = float(costo_total_salida)
                    costo_total_movimiento = -costo_total_salida

                elif cant_entrada > 0:
                    costo_total_movimiento = Decimal(str(mov.costo_total))

                else:
                    costo_total_movimiento = Decimal('0')

                saldo_cant_actual += cant_entrada - cant_salida
                saldo_costo_actual += costo_total_movimiento

                if saldo_cant_actual <= 0:
                    saldo_costo_actual = Decimal('0')
                    saldo_cant_actual = Decimal('0')

                mov.saldo_cantidad = float(saldo_cant_actual.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP))
                mov.saldo_costo_total = float(saldo_costo_actual.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP))

            print(f"DEBUG: Recálculo completado para Producto ID: {prod_id}, Almacén ID: {alm_id}")

        print(f"DEBUG: Recálculo de Kardex finalizado.")

    def cargar_datos_iniciales(self):
        """Carga proveedores, productos y almacenes"""
        # Proveedores
        self.cmb_proveedor.clear()
        proveedores = self.session.query(Proveedor).filter_by(activo=True).order_by(Proveedor.razon_social).all()
        if not proveedores:
            QMessageBox.warning(self, "Sin proveedores", "No hay proveedores registrados.")
        for prov in proveedores:
            self.cmb_proveedor.addItem(f"{prov.ruc} - {prov.razon_social}", prov.id)
        self.cmb_proveedor.setCurrentIndex(-1)

        # Productos
        self.cmb_producto.clear()
        self.lista_completa_productos = self.session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
        if not self.lista_completa_productos:
            QMessageBox.warning(self, "Sin productos", "No hay productos registrados.")
        for prod in self.lista_completa_productos:
            self.cmb_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)
        self.cmb_producto.setCurrentIndex(-1)

        # Almacenes
        self.cargar_almacenes()

        # Tipo de cambio
        self.actualizar_tipo_cambio()

    def cargar_almacenes(self):
        """Carga almacenes de todas las empresas activas"""
        self.cmb_almacen.clear()
        empresas = self.session.query(Empresa).filter_by(activo=True).all()
        for empresa in empresas:
            almacenes = self.session.query(Almacen).filter_by(
                empresa_id=empresa.id,
                activo=True
            ).all()
            for alm in almacenes:
                self.cmb_almacen.addItem(
                    f"{empresa.razon_social} - {alm.nombre}",
                    alm.id
                )
        self.cmb_almacen.setCurrentIndex(-1)

    def proveedor_seleccionado(self):
        """Muestra info del proveedor seleccionado"""
        prov_id = self.cmb_proveedor.currentData()
        if prov_id:
            prov = self.session.query(Proveedor).get(prov_id)
            if prov:
                info = f"📞 {prov.telefono or 'Sin teléfono'}"
                if prov.email:
                    info += f" | ✉️ {prov.email}"
                self.lbl_proveedor_info.setText(info)

    def fecha_cambiada(self):
        """Cuando cambia la fecha, busca tipo de cambio"""
        self.actualizar_tipo_cambio()

    def moneda_cambiada(self):
        """Cuando cambia la moneda"""
        es_dolares = self.cmb_moneda.currentData() == Moneda.DOLARES.value
        self.spn_tipo_cambio.setEnabled(es_dolares)
        if es_dolares:
            self.actualizar_tipo_cambio()
        else:
            self.spn_tipo_cambio.setValue(1.000)
        self.recalcular_totales()

    def actualizar_tipo_cambio(self):
        """Busca el tipo de cambio para la fecha seleccionada"""
        if self.cmb_moneda.currentData() != Moneda.DOLARES.value:
            return
        fecha = self.date_fecha.date().toPyDate()
        tc = self.session.query(TipoCambio).filter_by(fecha=fecha).first()
        if tc:
            self.spn_tipo_cambio.setValue(tc.precio_venta)
            self.lbl_tc_info.setText(f"✓ TC del {fecha.strftime('%d/%m/%Y')}")
            self.lbl_tc_info.setStyleSheet("color: #34a853; font-size: 10px;")
        else:
            self.lbl_tc_info.setText(f"⚠️ No hay TC para {fecha.strftime('%d/%m/%Y')}")
            self.lbl_tc_info.setStyleSheet("color: #f9ab00; font-size: 10px;")

    def agregar_producto(self):
        """Agrega un producto a la lista"""
        prod_id = self.cmb_producto.currentData()
        alm_id = self.cmb_almacen.currentData()
        cantidad = self.spn_cantidad.value()
        precio = self.spn_precio.value()

        if not prod_id or not alm_id:
            QMessageBox.warning(self, "Error", "Seleccione producto y almacén")
            return
        if cantidad <= 0 or precio < 0: # Permitir precio 0
            QMessageBox.warning(self, "Error", "Cantidad debe ser mayor a cero")
            return

        producto = self.session.query(Producto).get(prod_id)
        almacen = self.session.query(Almacen).get(alm_id)

        detalle = {
            'producto_id': prod_id,
            'producto_nombre': f"{producto.codigo} - {producto.nombre}",
            'almacen_id': alm_id,
            'almacen_nombre': almacen.nombre,
            'cantidad': cantidad,
            'precio_unitario': precio,
            'subtotal': cantidad * precio
        }

        self.detalles_compra.append(detalle)
        self.actualizar_tabla_productos()
        self.recalcular_totales()

        # Limpiar
        self.spn_cantidad.setValue(1.00)
        self.spn_precio.setValue(0.00)
        self.cmb_producto.setCurrentIndex(-1)
        self.cmb_producto.lineEdit().clear()

    def actualizar_tabla_productos(self):
        """Actualiza la tabla de productos y hace editables Cantidad/Precio."""
        self.tabla_productos.blockSignals(True)
        self.tabla_productos.setRowCount(len(self.detalles_compra))

        for row, det in enumerate(self.detalles_compra):
            # --- PRODUCTO (COMBOBOX) ---
            combo_producto = SearchableComboBox(self.tabla_productos)
            for prod in self.lista_completa_productos:
                combo_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)

            index_actual = combo_producto.findData(det['producto_id'])
            if index_actual != -1:
                combo_producto.setCurrentIndex(index_actual)

            # Conectar la señal ANTES de añadir a la tabla podría ser más seguro
            combo_producto.currentIndexChanged.connect(
                lambda index, r=row: self.producto_en_detalle_editado(index, r)
            )
            self.tabla_productos.setCellWidget(row, 0, combo_producto)

            # --- RESTO DE LAS CELDAS ---
            item_alm = QTableWidgetItem(det['almacen_nombre'])
            item_alm.setFlags(item_alm.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla_productos.setItem(row, 1, item_alm)


            item_cant = QTableWidgetItem(f"{det['cantidad']:.2f}")
            item_precio = QTableWidgetItem(f"{det['precio_unitario']:.2f}")
            self.tabla_productos.setItem(row, 2, item_cant)
            self.tabla_productos.setItem(row, 3, item_precio)

            item_subtotal = QTableWidgetItem(f"{det['subtotal']:.2f}")
            item_subtotal.setFlags(item_subtotal.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla_productos.setItem(row, 4, item_subtotal)

            btn_eliminar = QPushButton("✕")
            btn_eliminar.setStyleSheet("background-color: #ea4335; color: white; border-radius: 3px;")
            btn_eliminar.clicked.connect(lambda checked, r=row: self.eliminar_producto(r))
            self.tabla_productos.setCellWidget(row, 5, btn_eliminar)

        self.tabla_productos.blockSignals(False)
        try:
            self.tabla_productos.cellChanged.disconnect(self.detalle_editado)
        except TypeError:
            pass
        self.tabla_productos.cellChanged.connect(self.detalle_editado)

    def eliminar_producto(self, row):
        """Elimina un producto de la lista"""
        if 0 <= row < len(self.detalles_compra):
            del self.detalles_compra[row]
            self.actualizar_tabla_productos()
            self.recalcular_totales()

    def _calcular_montos_decimal(self):
        """
        Función interna que calcula los totales usando Decimal.
        Retorna (subtotal_sin_igv, igv, total, subtotal_productos, costo_adicional)
        """
        subtotal_productos = sum(Decimal(str(det['subtotal'])) for det in self.detalles_compra)
        costo_adicional = Decimal(str(self.spn_costo_adicional.value()))

        IGV_FACTOR = Decimal('1.18')
        IGV_PORCENTAJE = Decimal('0.18')
        DOS_DECIMALES = Decimal('0.01')

        if self.chk_incluye_igv.isChecked():
            total_con_igv = subtotal_productos + costo_adicional
            subtotal_sin_igv = (total_con_igv / IGV_FACTOR).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            igv = (total_con_igv - subtotal_sin_igv).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            total = total_con_igv.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
        else:
            subtotal_sin_igv = (subtotal_productos + costo_adicional).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            igv = (subtotal_sin_igv * IGV_PORCENTAJE).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
            total = (subtotal_sin_igv + igv).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

        return subtotal_sin_igv, igv, total, subtotal_productos, costo_adicional

    def recalcular_totales(self):
        """Recalcula los totales para mostrarlos en la UI."""
        subtotal_sin_igv, igv, total, _, _ = self._calcular_montos_decimal()
        moneda_simbolo = "S/" if self.cmb_moneda.currentData() == Moneda.SOLES.value else "$"
        self.lbl_subtotal.setText(f"{moneda_simbolo} {subtotal_sin_igv:.2f}")
        self.lbl_igv.setText(f"{moneda_simbolo} {igv:.2f}")
        self.lbl_total.setText(f"{moneda_simbolo} {total:.2f}")

    def guardar_compra(self):
        """Guarda una compra nueva o actualiza una existente, ajustando el Kardex."""
        try:
            fecha_doc = self.date_fecha.date().toPyDate()
            fecha_contable = self.date_fecha_contable.date().toPyDate()
            verificar_estado_anio(fecha_contable)

            if not self.cmb_proveedor.currentData():
                QMessageBox.warning(self, "Error", "Seleccione un proveedor")
                return

            serie = self.txt_serie_doc.text().strip()
            numero = self.txt_numero_doc.text().strip()
            if not serie or not numero:
                QMessageBox.warning(self, "Error", "Debe ingresar la serie y el número del documento")
                return

            numero_documento_completo = f"{serie}-{numero}"

            if not self.detalles_compra and self.compra_original is None:
                QMessageBox.warning(self, "Error", "Agregue al menos un producto")
                return

            es_edicion = self.compra_original is not None

            subtotal, igv, total, subtotal_productos_ui, costo_adicional = self._calcular_montos_decimal()

            if es_edicion:
                compra = self.session.get(Compra, self.compra_original.id)
                if not compra:
                    raise Exception(f"No se pudo encontrar la Compra ID {self.compra_original.id} en la sesión del diálogo.")

                compra.proveedor_id = self.cmb_proveedor.currentData()
                compra.tipo_documento = TipoDocumento(self.cmb_tipo_doc.currentData())
                compra.numero_documento = numero_documento_completo
                compra.moneda = Moneda(self.cmb_moneda.currentData())
                compra.tipo_cambio = Decimal(str(self.spn_tipo_cambio.value()))
                compra.incluye_igv = self.chk_incluye_igv.isChecked()
                compra.subtotal = subtotal
                compra.igv = igv
                compra.total = total
                compra.fecha_registro_contable = self.date_fecha_contable.date().toPyDate()
                compra.costo_adicional = costo_adicional if costo_adicional > 0 else None
                compra.descripcion_costo = self.txt_desc_costo.text().strip() or None
                compra.observaciones = self.txt_observaciones.toPlainText().strip() or None

            else:
                compra = Compra(
                    proveedor_id=self.cmb_proveedor.currentData(),
                    fecha=fecha_doc,
                    fecha_registro_contable=self.date_fecha_contable.date().toPyDate(),
                    tipo_documento=TipoDocumento(self.cmb_tipo_doc.currentData()),
                    numero_documento=numero_documento_completo,
                    moneda=Moneda(self.cmb_moneda.currentData()),
                    tipo_cambio=Decimal(str(self.spn_tipo_cambio.value())),
                    incluye_igv=self.chk_incluye_igv.isChecked(),
                    igv_porcentaje=Decimal('18.0'),
                    subtotal=subtotal,
                    igv=igv,
                    total=total,
                    costo_adicional=costo_adicional if costo_adicional > 0 else None,
                    descripcion_costo=self.txt_desc_costo.text().strip() or None,
                    observaciones=self.txt_observaciones.toPlainText().strip() or None
                )
                self.session.add(compra)
                self.session.flush()

            ids_detalles_ui = {det.get('detalle_original_id') for det in self.detalles_compra if det.get('detalle_original_id')}
            ids_detalles_originales = {det.id for det in self.detalles_originales_obj} if es_edicion else set()

            detalles_a_eliminar_ids = ids_detalles_originales - ids_detalles_ui
            detalles_a_anadir_ui = [det for det in self.detalles_compra if not det.get('detalle_original_id')]
            detalles_a_modificar_ui = [det for det in self.detalles_compra if det.get('detalle_original_id') in ids_detalles_originales]

            DOS_DECIMALES = Decimal('0.01')
            IGV_FACTOR = Decimal('1.18')
            movimientos_kardex = []
            producto_almacen_afectados = set()

            if es_edicion and detalles_a_eliminar_ids:
                for detalle_id in detalles_a_eliminar_ids:
                    detalle_obj = self.session.get(CompraDetalle, detalle_id)
                    if detalle_obj:
                         producto_almacen_afectados.add((detalle_obj.producto_id, detalle_obj.almacen_id))
                         mov_original = self.session.query(MovimientoStock).filter_by(
                             tipo=TipoMovimiento.COMPRA, tipo_documento=compra.tipo_documento,
                             numero_documento=self.compra_original.numero_documento,
                             producto_id=detalle_obj.producto_id, almacen_id=detalle_obj.almacen_id,
                         ).order_by(MovimientoStock.id.desc()).first()

                         if mov_original:
                             ajuste_salida = MovimientoStock(
                                 empresa_id=mov_original.empresa_id, producto_id=mov_original.producto_id, almacen_id=mov_original.almacen_id,
                                 tipo=TipoMovimiento.DEVOLUCION_COMPRA,
                                 tipo_documento=compra.tipo_documento, numero_documento=compra.numero_documento,
                                 fecha_documento=compra.fecha, proveedor_id=compra.proveedor_id,
                                 cantidad_entrada=0, cantidad_salida=mov_original.cantidad_entrada,
                                 costo_unitario=mov_original.costo_unitario, costo_total=mov_original.costo_total,
                                 saldo_cantidad=0, saldo_costo_total=0, moneda=compra.moneda, tipo_cambio=float(compra.tipo_cambio),
                                 observaciones=f"Ajuste por edición de compra ID {compra.id} (Detalle ID {detalle_id} eliminado)"
                             )
                             movimientos_kardex.append(ajuste_salida)
                         else:
                              print(f"ADVERTENCIA: No se encontró MovimientoStock original para el detalle eliminado ID {detalle_id}")
                         self.session.delete(detalle_obj)
                         print(f"DEBUG: Detalle {detalle_id} eliminado.")
                    else:
                         print(f"ADVERTENCIA: No se encontró Detalle {detalle_id} para eliminar.")

            for det_ui in detalles_a_anadir_ui:
                cantidad_dec = Decimal(str(det_ui['cantidad']))
                precio_unitario_ui = Decimal(str(det_ui['precio_unitario']))
                if self.chk_incluye_igv.isChecked():
                    precio_sin_igv = (precio_unitario_ui / IGV_FACTOR).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                else:
                    precio_sin_igv = precio_unitario_ui
                subtotal_det_sin_igv = (cantidad_dec * precio_sin_igv).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                subtotal_base_prorrateo = sum(
                    (Decimal(str(d['cantidad'])) * (Decimal(str(d['precio_unitario'])) / (IGV_FACTOR if self.chk_incluye_igv.isChecked() else Decimal('1'))))
                    for d in self.detalles_compra
                ).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                costo_unitario_final = precio_sin_igv
                if costo_adicional > 0 and subtotal_base_prorrateo > 0:
                    proporcion = subtotal_det_sin_igv / subtotal_base_prorrateo if subtotal_base_prorrateo != 0 else Decimal('0')
                    costo_prorrateado = (costo_adicional * proporcion).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                    if cantidad_dec != 0:
                       costo_unitario_final += (costo_prorrateado / cantidad_dec).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                subtotal_final_det = (cantidad_dec * costo_unitario_final).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

                nuevo_detalle = CompraDetalle()
                nuevo_detalle.compra_id = compra.id
                nuevo_detalle.producto_id = det_ui['producto_id']
                nuevo_detalle.almacen_id = det_ui['almacen_id']
                nuevo_detalle.cantidad = cantidad_dec
                nuevo_detalle.precio_unitario_sin_igv = costo_unitario_final
                nuevo_detalle.subtotal = subtotal_final_det
                self.session.add(nuevo_detalle)

                producto_almacen_afectados.add((det_ui['producto_id'], det_ui['almacen_id']))

                almacen = self.session.get(Almacen, det_ui['almacen_id'])
                if almacen:
                    nuevo_movimiento = MovimientoStock(
                        empresa_id=almacen.empresa_id, producto_id=det_ui['producto_id'], almacen_id=det_ui['almacen_id'],
                        tipo=TipoMovimiento.COMPRA,
                        tipo_documento=compra.tipo_documento, numero_documento=compra.numero_documento,
                        fecha_documento=compra.fecha, proveedor_id=compra.proveedor_id,
                        cantidad_entrada=cantidad_dec, cantidad_salida=0,
                        costo_unitario=float(costo_unitario_final), costo_total=float(subtotal_final_det),
                        saldo_cantidad=0, saldo_costo_total=0,
                        moneda=compra.moneda, tipo_cambio=float(compra.tipo_cambio),
                        observaciones=f"Registro por {'edición (añadido)' if es_edicion else 'nueva compra'} ID {compra.id}"
                    )
                    movimientos_kardex.append(nuevo_movimiento)
                else:
                     print(f"ADVERTENCIA: No se encontró Almacén ID {det_ui['almacen_id']} para añadir movimiento.")
                print(f"DEBUG: Detalle nuevo añadido para producto {det_ui['producto_id']}.")

            if es_edicion:
                 for det_ui in detalles_a_modificar_ui:
                     detalle_obj = self.session.get(CompraDetalle, det_ui['detalle_original_id'])
                     if not detalle_obj:
                         print(f"ADVERTENCIA: No se encontró detalle original ID {det_ui['detalle_original_id']} para modificar.")
                         continue

                     cantidad_original_dec = Decimal(str(detalle_obj.cantidad))
                     costo_unitario_original_dec = Decimal(str(detalle_obj.precio_unitario_sin_igv))
                     costo_total_original_dec = Decimal(str(detalle_obj.subtotal))
                     producto_id_original = detalle_obj.producto_id
                     almacen_id_original = detalle_obj.almacen_id

                     producto_almacen_afectados.add((producto_id_original, almacen_id_original))

                     cantidad_dec = Decimal(str(det_ui['cantidad']))
                     precio_unitario_ui = Decimal(str(det_ui['precio_unitario']))
                     if self.chk_incluye_igv.isChecked():
                         precio_sin_igv = (precio_unitario_ui / IGV_FACTOR).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                     else:
                         precio_sin_igv = precio_unitario_ui
                     subtotal_det_sin_igv = (cantidad_dec * precio_sin_igv).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                     subtotal_base_prorrateo = sum(
                         (Decimal(str(d['cantidad'])) * (Decimal(str(d['precio_unitario'])) / (IGV_FACTOR if self.chk_incluye_igv.isChecked() else Decimal('1'))))
                         for d in self.detalles_compra
                     ).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                     costo_unitario_final = precio_sin_igv
                     if costo_adicional > 0 and subtotal_base_prorrateo > 0:
                         proporcion = subtotal_det_sin_igv / subtotal_base_prorrateo if subtotal_base_prorrateo != 0 else Decimal('0')
                         costo_prorrateado = (costo_adicional * proporcion).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                         if cantidad_dec != 0:
                            costo_unitario_final += (costo_prorrateado / cantidad_dec).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                     subtotal_final_det = (cantidad_dec * costo_unitario_final).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

                     detalle_obj.producto_id = det_ui['producto_id']
                     detalle_obj.almacen_id = det_ui['almacen_id']
                     detalle_obj.cantidad = cantidad_dec
                     detalle_obj.precio_unitario_sin_igv = costo_unitario_final
                     detalle_obj.subtotal = subtotal_final_det

                     producto_almacen_afectados.add((detalle_obj.producto_id, detalle_obj.almacen_id))

                     if (detalle_obj.producto_id != producto_id_original or detalle_obj.almacen_id != almacen_id_original):
                         mov_original = self.session.query(MovimientoStock).filter_by(
                             tipo=TipoMovimiento.COMPRA, tipo_documento=compra.tipo_documento,
                             numero_documento=self.compra_original.numero_documento,
                             producto_id=producto_id_original, almacen_id=almacen_id_original
                         ).order_by(MovimientoStock.id.desc()).first()
                         if mov_original:
                             ajuste_salida = MovimientoStock(
                                 empresa_id=mov_original.empresa_id, producto_id=mov_original.producto_id, almacen_id=mov_original.almacen_id,
                                 tipo=TipoMovimiento.DEVOLUCION_COMPRA,
                                 tipo_documento=compra.tipo_documento, numero_documento=compra.numero_documento,
                                 fecha_documento=compra.fecha, proveedor_id=compra.proveedor_id,
                                 cantidad_entrada=0, cantidad_salida=mov_original.cantidad_entrada,
                                 costo_unitario=mov_original.costo_unitario, costo_total=mov_original.costo_total,
                                 saldo_cantidad=0, saldo_costo_total=0, moneda=compra.moneda, tipo_cambio=float(compra.tipo_cambio),
                                 observaciones=f"Ajuste (salida) por cambio Prod/Alm en edición Compra ID {compra.id} (Detalle ID {detalle_obj.id})"
                             )
                             movimientos_kardex.append(ajuste_salida)
                         almacen_nuevo = self.session.get(Almacen, detalle_obj.almacen_id)
                         if almacen_nuevo:
                             ajuste_entrada = MovimientoStock(
                                 empresa_id=almacen_nuevo.empresa_id, producto_id=detalle_obj.producto_id, almacen_id=detalle_obj.almacen_id,
                                 tipo=TipoMovimiento.COMPRA,
                                 tipo_documento=compra.tipo_documento, numero_documento=compra.numero_documento,
                                 fecha_documento=compra.fecha, proveedor_id=compra.proveedor_id,
                                 cantidad_entrada=cantidad_dec, cantidad_salida=0,
                                 costo_unitario=float(costo_unitario_final), costo_total=float(subtotal_final_det),
                                 saldo_cantidad=0, saldo_costo_total=0, moneda=compra.moneda, tipo_cambio=float(compra.tipo_cambio),
                                 observaciones=f"Ajuste (entrada) por cambio Prod/Alm en edición Compra ID {compra.id} (Detalle ID {detalle_obj.id})"
                             )
                             movimientos_kardex.append(ajuste_entrada)
                     else:
                         dif_cantidad = cantidad_dec - cantidad_original_dec
                         dif_costo_total = subtotal_final_det - costo_total_original_dec
                         if dif_cantidad != 0 or dif_costo_total != 0:
                             almacen = self.session.get(Almacen, detalle_obj.almacen_id)
                             if almacen:
                                 tipo_ajuste = TipoMovimiento.AJUSTE_POSITIVO if dif_cantidad >= 0 else TipoMovimiento.AJUSTE_NEGATIVO
                                 cant_ent = max(Decimal('0'), dif_cantidad)
                                 cant_sal = max(Decimal('0'), -dif_cantidad)
                                 costo_unit_ajuste = Decimal('0')
                                 if cant_ent > 0:
                                     costo_unit_ajuste = (dif_costo_total / cant_ent).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP) if cant_ent != 0 else Decimal('0')
                                 elif cant_sal > 0:
                                     costo_unit_ajuste = costo_unitario_original_dec
                                     dif_costo_total = (cant_sal * costo_unit_ajuste).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                                 ajuste_mov = MovimientoStock(
                                     empresa_id=almacen.empresa_id, producto_id=detalle_obj.producto_id, almacen_id=detalle_obj.almacen_id,
                                     tipo=tipo_ajuste,
                                     tipo_documento=compra.tipo_documento, numero_documento=compra.numero_documento,
                                     fecha_documento=compra.fecha, proveedor_id=compra.proveedor_id,
                                     cantidad_entrada=cant_ent, cantidad_salida=cant_sal,
                                     costo_unitario=float(costo_unit_ajuste), costo_total=float(dif_costo_total),
                                     saldo_cantidad=0, saldo_costo_total=0,
                                     moneda=compra.moneda, tipo_cambio=float(compra.tipo_cambio),
                                     observaciones=f"Ajuste por edición Compra ID {compra.id} (Detalle ID {detalle_obj.id})"
                                 )
                                 movimientos_kardex.append(ajuste_mov)
                     print(f"DEBUG: Detalle {detalle_obj.id} modificado.")

            for mov in movimientos_kardex:
                self.session.add(mov)

            if producto_almacen_afectados:
                 print(f"DEBUG: Productos/Almacenes afectados: {producto_almacen_afectados}")
                 self.session.flush()
                 self.recalcular_kardex_posterior(producto_almacen_afectados, compra.fecha)
            else:
                 print("DEBUG: No hubo movimientos de kardex que requieran recálculo.")


            print(f"DEBUG (guardar_compra PRE-COMMIT): Intentando guardar Compra ID {compra.id}")
            print(f"  -> Subtotal={compra.subtotal}, IGV={compra.igv}, Total={compra.total}")

            self.session.commit()
            print(f"DEBUG (guardar_compra POST-COMMIT): Commit realizado.")
            QMessageBox.information(self, "Éxito", f"Compra {'actualizada' if es_edicion else 'registrada'} exitosamente.")
            self.accept()

        except AnioCerradoError as e:
            QMessageBox.warning(self, "Operación no permitida", str(e))
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al {'actualizar' if es_edicion else 'guardar'} compra:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def cargar_datos_para_edicion(self):
        """Rellena los campos del diálogo con los datos de la compra a editar, bloqueando señales."""
        if not self.compra_original:
            return

        widgets_a_bloquear = [
            self.cmb_proveedor, self.date_fecha, self.date_fecha_contable,
            self.cmb_tipo_doc, self.txt_serie_doc, self.txt_numero_doc,
            self.cmb_moneda, self.spn_tipo_cambio, self.chk_incluye_igv,
            self.spn_costo_adicional, self.txt_desc_costo,
            self.txt_observaciones, self.tabla_productos
        ]
        signal_states = {widget: widget.signalsBlocked() for widget in widgets_a_bloquear}
        for widget in widgets_a_bloquear:
             widget.blockSignals(True)

        try:
            self.setWindowTitle(f"✏️ Editando Compra: {self.compra_original.numero_documento}")
            self.btn_guardar.setText("Guardar Cambios")

            index_prov = self.cmb_proveedor.findData(self.compra_original.proveedor_id)
            if index_prov != -1:
                self.cmb_proveedor.setCurrentIndex(index_prov)
            else:
                 QMessageBox.warning(self, "Proveedor no encontrado", f"El proveedor original (ID: {self.compra_original.proveedor_id}) no está activo o no existe.")

            self.date_fecha.setDate(QDate(self.compra_original.fecha.year,
                                           self.compra_original.fecha.month,
                                           self.compra_original.fecha.day))

            fecha_contable_guardada = getattr(self.compra_original, 'fecha_registro_contable', None)
            if fecha_contable_guardada:
                self.date_fecha_contable.setDate(QDate(fecha_contable_guardada.year,
                                                        fecha_contable_guardada.month,
                                                        fecha_contable_guardada.day))
            else:
                self.date_fecha_contable.setDate(self.date_fecha.date())

            index_td = self.cmb_tipo_doc.findData(self.compra_original.tipo_documento.value)
            if index_td != -1:
                self.cmb_tipo_doc.setCurrentIndex(index_td)

            try:
                serie, numero = self.compra_original.numero_documento.split('-', 1)
                self.txt_serie_doc.setText(serie)
                self.txt_numero_doc.setText(numero)
            except ValueError:
                 self.txt_serie_doc.setText("")
                 self.txt_numero_doc.setText(self.compra_original.numero_documento)

            index_moneda = self.cmb_moneda.findData(self.compra_original.moneda.value)
            if index_moneda != -1:
                self.cmb_moneda.setCurrentIndex(index_moneda)
                es_dolares = self.compra_original.moneda == Moneda.DOLARES
                self.spn_tipo_cambio.setEnabled(es_dolares)
                if es_dolares:
                    self.spn_tipo_cambio.setValue(float(self.compra_original.tipo_cambio))
                    fecha_dt = self.compra_original.fecha
                    tc = self.session.query(TipoCambio).filter_by(fecha=fecha_dt).first()
                    if tc:
                        self.lbl_tc_info.setText(f"✓ TC del {fecha_dt.strftime('%d/%m/%Y')}")
                        self.lbl_tc_info.setStyleSheet("color: #34a853; font-size: 10px;")
                    else:
                        self.lbl_tc_info.setText(f"⚠️ No hay TC para {fecha_dt.strftime('%d/%m/%Y')}")
                        self.lbl_tc_info.setStyleSheet("color: #f9ab00; font-size: 10px;")
                else:
                    self.spn_tipo_cambio.setValue(1.000)
                    self.lbl_tc_info.setText("Tipo cambio VENTA")
                    self.lbl_tc_info.setStyleSheet("color: #666; font-size: 10px;")

            self.chk_incluye_igv.setChecked(self.compra_original.incluye_igv)
            self.spn_costo_adicional.setValue(float(self.compra_original.costo_adicional or 0))
            self.txt_desc_costo.setText(self.compra_original.descripcion_costo or "")
            self.txt_observaciones.setPlainText(self.compra_original.observaciones or "")

            self.detalles_compra = []
            for det_obj in self.detalles_originales_obj:
                producto = self.session.query(Producto).get(det_obj.producto_id)
                almacen = self.session.query(Almacen).get(det_obj.almacen_id)
                if not producto or not almacen:
                     QMessageBox.warning(self, "Error de Datos", f"No se encontró el producto (ID: {det_obj.producto_id}) o almacén (ID: {det_obj.almacen_id}) original.")
                     continue

                cantidad_orig = Decimal(str(det_obj.cantidad))
                precio_kardex_sin_igv = Decimal(str(det_obj.precio_unitario_sin_igv))

                # --- LÓGICA CORREGIDA PARA PRECIO UI ---
                precio_ui = precio_kardex_sin_igv
                if self.compra_original.incluye_igv:
                    precio_ui = (precio_ui * Decimal('1.18')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                # 'subtotal_ui' ahora se define aquí
                subtotal_ui = (cantidad_orig * precio_ui).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                # --- FIN CORRECCIÓN ---

                detalle_dict = {
                     'producto_id': det_obj.producto_id,
                     'producto_nombre': f"{producto.codigo} - {producto.nombre}",
                     'almacen_id': det_obj.almacen_id,
                     'almacen_nombre': almacen.nombre,
                     'cantidad': float(cantidad_orig),
                     'precio_unitario': float(precio_ui),
                     'subtotal': float(subtotal_ui),
                     'detalle_original_id': det_obj.id
                }
                self.detalles_compra.append(detalle_dict)

            self.actualizar_tabla_productos()

        finally:
             for widget, original_state in signal_states.items():
                  widget.blockSignals(original_state)

        self.recalcular_totales()

    def producto_en_detalle_editado(self, combo_index, row):
        """
        Maneja el cambio de un producto en el ComboBox de la tabla de detalles.
        """
        if 0 <= row < len(self.detalles_compra):
            combo_box = self.tabla_productos.cellWidget(row, 0)
            if not combo_box:
                return

            nuevo_producto_id = combo_box.itemData(combo_index)
            nuevo_producto_nombre = combo_box.itemText(combo_index)

            if nuevo_producto_id is not None:
                detalle_actualizado = self.detalles_compra[row]
                detalle_actualizado['producto_id'] = nuevo_producto_id
                detalle_actualizado['producto_nombre'] = nuevo_producto_nombre
            else:
                print(f"ADVERTENCIA: No se pudo obtener el ID del producto para el índice {combo_index} en la fila {row}")

    def detalle_editado(self, row, column):
        if column not in [2, 3]:
            return
        item = self.tabla_productos.item(row, column)
        if not item:
            return
        nuevo_valor_str = item.text().replace(',', '.')

        try:
            nuevo_valor = float(nuevo_valor_str)
            if nuevo_valor < 0:
                 raise ValueError("Valor no puede ser negativo")
        except ValueError:
            QMessageBox.warning(self, "Valor inválido", f"Ingrese un número válido.")
            self.tabla_productos.blockSignals(True)
            if column == 2:
                 item.setText(f"{self.detalles_compra[row]['cantidad']:.2f}")
            else:
                 item.setText(f"{self.detalles_compra[row]['precio_unitario']:.2f}")
            self.tabla_productos.blockSignals(False)
            return

        detalle_actualizado = self.detalles_compra[row]
        if column == 2:
            detalle_actualizado['cantidad'] = nuevo_valor
        else:
            detalle_actualizado['precio_unitario'] = nuevo_valor

        cantidad_actual = detalle_actualizado['cantidad']
        precio_actual = detalle_actualizado['precio_unitario']
        detalle_actualizado['subtotal'] = cantidad_actual * precio_actual

        self.tabla_productos.blockSignals(True)
        subtotal_item = self.tabla_productos.item(row, 4)
        if not subtotal_item:
             subtotal_item = QTableWidgetItem()
             subtotal_item.setFlags(subtotal_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
             self.tabla_productos.setItem(row, 4, subtotal_item)
        subtotal_item.setText(f"{detalle_actualizado['subtotal']:.2f}")
        self.tabla_productos.blockSignals(False)

        self.recalcular_totales()

    def sincronizar_fecha_contable(self, nueva_fecha):
        self.date_fecha_contable.setDate(nueva_fecha)

    def formatear_numero_documento(self):
        texto_actual = self.txt_numero_doc.text().strip()
        if texto_actual.isdigit():
            nuevo_texto = texto_actual.zfill(8)
            self.txt_numero_doc.setText(nuevo_texto)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:

                if source is self.cmb_producto:
                    if self.cmb_producto.completer().popup().isVisible():
                        return super().eventFilter(source, event)
                    self.cmb_almacen.setFocus()
                    return True

                elif source is self.cmb_almacen:
                    if hasattr(self.cmb_almacen, 'completer') and self.cmb_almacen.completer() and self.cmb_almacen.completer().popup().isVisible():
                         return super().eventFilter(source, event)
                    self.spn_cantidad.setFocus()
                    return True

                elif source is self.spn_cantidad:
                    self.spn_precio.setFocus()
                    return True

                elif source is self.spn_precio:
                    self.btn_agregar.setFocus()
                    self.btn_agregar.animateClick()
                    return True

                elif source is self.btn_agregar:
                    self.cmb_producto.setFocus()
                    return True

        return super().eventFilter(source, event)

    def crear_nuevo_proveedor(self):
        """
        Abre el diálogo para crear un nuevo proveedor y
        recarga el ComboBox de proveedores.
        """
        if ProveedorDialog is None:
            QMessageBox.critical(self, "Error",
                "El módulo de proveedores ('proveedores_window.py') no se pudo cargar.\n"
                "Asegúrese de que el archivo existe y que la clase se llama 'ProveedorDialog'.")
            return

        dialog = ProveedorDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            print("DEBUG: ProveedorDialog aceptado. Recargando datos iniciales.")
            texto_actual = self.cmb_proveedor.lineEdit().text()

            # Solo recargar proveedores
            self.cmb_proveedor.clear()
            proveedores = self.session.query(Proveedor).filter_by(activo=True).order_by(Proveedor.razon_social).all()
            for prov in proveedores:
                self.cmb_proveedor.addItem(f"{prov.ruc} - {prov.razon_social}", prov.id)

            lista_nombres_proveedores = [self.cmb_proveedor.itemText(i) for i in range(self.cmb_proveedor.count())]
            completer_proveedor = QCompleter(lista_nombres_proveedores, self)
            completer_proveedor.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer_proveedor.setFilterMode(Qt.MatchFlag.MatchContains)
            self.cmb_proveedor.setCompleter(completer_proveedor)

            self.cmb_proveedor.lineEdit().setText(texto_actual)

            # Opcional: Seleccionar el nuevo proveedor si el diálogo lo retorna
            if hasattr(dialog, 'nuevo_proveedor_id') and dialog.nuevo_proveedor_id:
               index = self.cmb_proveedor.findData(dialog.nuevo_proveedor_id)
               if index != -1:
                   self.cmb_proveedor.setCurrentIndex(index)

    def crear_nuevo_producto(self):
        """
        Abre el diálogo para crear un nuevo producto y
        recarga el ComboBox de productos.
        """
        dialog = ProductoDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            print("DEBUG: ProductoDialog aceptado. Recargando productos.")
            texto_actual = self.cmb_producto.lineEdit().text()

            # Solo recargar productos
            self.cmb_producto.clear()
            productos = self.session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
            for prod in productos:
                self.cmb_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)

            lista_nombres_productos = [self.cmb_producto.itemText(i) for i in range(self.cmb_producto.count())]
            completer = QCompleter(lista_nombres_productos, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.cmb_producto.setCompleter(completer)

            self.cmb_producto.lineEdit().setText(texto_actual)

            # (El código para seleccionar el nuevo producto se omite por simplicidad)

# ============================================
# DIÁLOGO DE VER DETALLE (CORREGIDO)
# ============================================

class DetalleCompraDialog(QDialog):
    """Diálogo de solo lectura para mostrar el detalle de una compra."""

    def __init__(self, compra, detalles, session, parent=None):
        super().__init__(parent)
        self.compra = compra
        self.detalles = detalles
        self.session = session
        self.setWindowTitle(f"Detalle: {compra.tipo_documento.value} {compra.numero_documento}")
        self.setMinimumSize(800, 600)

        self.lbl_subtotal_detalle = None
        self.lbl_igv_detalle = None
        self.lbl_total_detalle = None

        self.init_ui()
        self.recalcular_totales_locales()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # --- Grupo de Datos Generales ---
        grupo_datos = QGroupBox("Datos Generales")
        form_datos = QFormLayout()
        form_datos.addRow(QLabel("<b>Proveedor:</b>"), QLabel(self.compra.proveedor.razon_social))
        form_datos.addRow(QLabel("<b>Fecha Emisión:</b>"), QLabel(self.compra.fecha.strftime('%d/%m/%Y')))

        f_contable_str = "--"
        if getattr(self.compra, 'fecha_registro_contable', None):
             f_contable_str = self.compra.fecha_registro_contable.strftime('%d/%m/%Y')
        form_datos.addRow(QLabel("<b>Fecha Contable:</b>"), QLabel(f_contable_str))

        form_datos.addRow(QLabel("<b>Documento:</b>"), QLabel(f"{self.compra.tipo_documento.value} {self.compra.numero_documento}"))
        moneda_str = f"{self.compra.moneda.value} (TC: {self.compra.tipo_cambio:.3f})" if self.compra.moneda == Moneda.DOLARES else "SOLES (S/)"
        form_datos.addRow(QLabel("<b>Moneda:</b>"), QLabel(moneda_str))
        igv_str = "Precios INCLUYEN IGV" if self.compra.incluye_igv else "Precios NO incluyen IGV"
        form_datos.addRow(QLabel("<b>Condición:</b>"), QLabel(igv_str))
        if self.compra.observaciones:
            form_datos.addRow(QLabel("<b>Obs:</b>"), QLabel(self.compra.observaciones))
        grupo_datos.setLayout(form_datos)
        layout.addWidget(grupo_datos)

        # --- Tabla de Productos ---
        layout.addWidget(QLabel("<b>Productos:</b>"))
        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(["Producto", "Almacén", "Cantidad", "P. Unit (sin IGV)", "Subtotal"])
        tabla.setRowCount(len(self.detalles))
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for row, det in enumerate(self.detalles):
            producto = self.session.query(Producto).get(det.producto_id)
            almacen = self.session.query(Almacen).get(det.almacen_id)

            producto_nombre = f"{producto.codigo} - {producto.nombre}" if producto else "N/A"
            almacen_nombre = almacen.nombre if almacen else "N/A"

            tabla.setItem(row, 0, QTableWidgetItem(producto_nombre))
            tabla.setItem(row, 1, QTableWidgetItem(almacen_nombre))
            tabla.setItem(row, 2, QTableWidgetItem(f"{det.cantidad:.2f}"))
            tabla.setItem(row, 3, QTableWidgetItem(f"{det.precio_unitario_sin_igv:.2f}"))
            tabla.setItem(row, 4, QTableWidgetItem(f"{det.subtotal:.2f}"))

        tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tabla.resizeColumnsToContents()
        layout.addWidget(tabla)

        # --- Grupo de Totales (CORREGIDO) ---
        grupo_totales = QGroupBox("Resumen de Totales")
        form_totales = QFormLayout()
        simbolo = "$" if self.compra.moneda == Moneda.DOLARES else "S/"

        costo_adicional_obj = getattr(self.compra, 'costo_adicional', None)
        if costo_adicional_obj is not None and costo_adicional_obj > 0:
             desc_costo = f"({self.compra.descripcion_costo})" if self.compra.descripcion_costo else ""
             costo_adicional_val = float(costo_adicional_obj)
             form_totales.addRow(QLabel("<b>Costo Adicional:</b>"), QLabel(f"{simbolo} {costo_adicional_val:.2f} {desc_costo}"))

        self.lbl_subtotal_detalle = QLabel(f"{simbolo} --.--")
        form_totales.addRow(QLabel("<b>Subtotal:</b>"), self.lbl_subtotal_detalle)

        self.lbl_igv_detalle = QLabel(f"{simbolo} --.--")
        form_totales.addRow(QLabel("<b>IGV (18%):</b>"), self.lbl_igv_detalle)

        self.lbl_total_detalle = QLabel(f"{simbolo} --.--")
        self.lbl_total_detalle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a73e8;")
        form_totales.addRow(QLabel("<b>TOTAL:</b>"), self.lbl_total_detalle)
        # --- FIN CORRECCIÓN ---

        grupo_totales.setLayout(form_totales)
        grupo_totales.setMaximumWidth(350)
        totales_layout = QHBoxLayout()
        totales_layout.addStretch()
        totales_layout.addWidget(grupo_totales)
        layout.addLayout(totales_layout)

        # --- Botón de cierre ---
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

    def recalcular_totales_locales(self):
        """
        Recalcula los totales basándose en los datos REALES de la compra.
        """
        if not all([self.lbl_subtotal_detalle, self.lbl_igv_detalle, self.lbl_total_detalle]):
             print("ERROR CRÍTICO: Etiquetas de totales no inicializadas.")
             return

        print(f"DEBUG: Recalculando totales locales para Compra ID {self.compra.id}")

        # --- CORRECCIÓN CLAVE: USAR LOS TOTALES DE LA COMPRA ---
        subtotal_real = Decimal(str(getattr(self.compra, 'subtotal', '0')))
        igv_real = Decimal(str(getattr(self.compra, 'igv', '0')))
        total_real = Decimal(str(getattr(self.compra, 'total', '0')))
        # --- FIN CORRECCIÓN ---

        simbolo = "$" if self.compra.moneda == Moneda.DOLARES else "S/"

        self.lbl_subtotal_detalle.setText(f"{simbolo} {subtotal_real:.2f}")
        self.lbl_igv_detalle.setText(f"{simbolo} {igv_real:.2f}")
        self.lbl_total_detalle.setText(f"{simbolo} {total_real:.2f}")

        print(f"DEBUG: Totales locales actualizados a: Sub={subtotal_real:.2f}, IGV={igv_real:.2f}, Total={total_real:.2f}")

# ============================================
# VENTANA PRINCIPAL DE COMPRAS (CORREGIDA)
# ============================================

class ComprasWindow(QWidget):
    """Ventana principal de compras"""

    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.init_ui()
        self.cargar_compras()

    def init_ui(self):
        self.setWindowTitle("Gestión de Compras")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        titulo = QLabel("🛒 Gestión de Compras")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")

        btn_nueva = QPushButton("+ Nueva Compra")
        btn_nueva.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: white;
                padding: 10px 20px; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1557b0; }
        """)
        btn_nueva.clicked.connect(self.nueva_compra)

        # --- LÓGICA DE LICENCIA (AGRUPADA) ---
        if self.user_info and self.user_info.get('licencia_vencida'):
            btn_nueva.setEnabled(False)
            btn_nueva.setToolTip("Licencia vencida - Solo consulta")

        # --- LAYOUT DEL HEADER (CORREGIDO) ---
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nueva)

        # Filtros (Reemplazados)
        filtro_layout = QHBoxLayout()

        # --- NUEVOS FILTROS DE PERIODO ---
        filtro_layout.addWidget(QLabel("<b>Periodo Contable:</b>"))

        self.cmb_mes_filtro = SearchableComboBox()
        meses_espanol = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        mes_actual = datetime.now().month
        for i, mes in enumerate(meses_espanol):
            self.cmb_mes_filtro.addItem(mes, i + 1) # Guardar el número de mes (1-12)
        self.cmb_mes_filtro.setCurrentIndex(mes_actual - 1) # Seleccionar mes actual

        # Conectar señales
        self.cmb_mes_filtro.currentIndexChanged.connect(self.cargar_compras)
        # --- FIN NUEVOS FILTROS ---

        self.cmb_proveedor_filtro = SearchableComboBox()
        self.cmb_proveedor_filtro.addItem("Todos los proveedores", None)
        self.cmb_proveedor_filtro.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed) # Que se expanda
        proveedores = self.session.query(Proveedor).join(Compra).filter(
            Proveedor.activo==True,
            extract('year', Compra.fecha) == app_context.get_selected_year()
        ).distinct().order_by(Proveedor.razon_social).all()
        for prov in proveedores:
            self.cmb_proveedor_filtro.addItem(prov.razon_social, prov.id)

        self.cmb_proveedor_filtro.currentIndexChanged.connect(self.cargar_compras)

        self.cmb_vista_moneda = QComboBox()
        self.cmb_vista_moneda.setFixedWidth(180)
        self.cmb_vista_moneda.addItem("Ver en Moneda de Origen", "ORIGEN")
        self.cmb_vista_moneda.addItem("Mostrar Todo en SOLES (S/)", "SOLES")
        self.cmb_vista_moneda.currentIndexChanged.connect(self.cargar_compras)

        # Añadir widgets al layout de filtros
        filtro_layout.addWidget(self.cmb_mes_filtro)
        filtro_layout.addWidget(self.cmb_proveedor_filtro)
        filtro_layout.addWidget(self.cmb_vista_moneda)
        filtro_layout.addStretch()

        # Contador
        self.lbl_contador = QLabel("Cargando...")
        self.lbl_contador.setStyleSheet("color: #666; font-size: 11px;")

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(9) # <--- CORREGIDO A 9
        self.tabla.setHorizontalHeaderLabels([
            "F. Contable", "F. Emisión", "Documento", "Proveedor", "Moneda", "Subtotal", "IGV", "Total", "Acciones"
        ])

        self.tabla.setStyleSheet("""
            QTableWidget { border: 1px solid #ddd; border-radius: 5px; background-color: white; }
            QHeaderView::section { background-color: #f1f3f4; padding: 10px; border: none; font-weight: bold; }
        """)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Proveedor
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed) # Acciones
        self.tabla.setColumnWidth(0, 90) # F. Contable
        self.tabla.setColumnWidth(1, 90) # F. Emisión
        self.tabla.setColumnWidth(8, 160) # Acciones

        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addLayout(header_layout)
        layout.addLayout(filtro_layout)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)

        self.setLayout(layout)

    def recalcular_kardex_posterior(self, producto_almacen_afectados, fecha_referencia):
        """
        Recalcula los saldos y costos del Kardex (copiado de CompraDialog).
        """
        print(f"DEBUG: Iniciando recálculo de Kardex para {len(producto_almacen_afectados)} pares desde {fecha_referencia}")
        DOS_DECIMALES = Decimal('0.01')
        SEIS_DECIMALES = Decimal('0.000001')

        for prod_id, alm_id in producto_almacen_afectados:
            print(f"DEBUG: Recalculando para Producto ID: {prod_id}, Almacén ID: {alm_id}")

            mov_anterior = self.session.query(MovimientoStock).filter(
                MovimientoStock.producto_id == prod_id,
                MovimientoStock.almacen_id == alm_id,
                MovimientoStock.fecha_documento < fecha_referencia
            ).order_by(MovimientoStock.fecha_documento.desc(), MovimientoStock.id.desc()).first()

            saldo_cant_actual = Decimal(str(mov_anterior.saldo_cantidad)) if mov_anterior else Decimal('0')
            saldo_costo_actual = Decimal(str(mov_anterior.saldo_costo_total)) if mov_anterior else Decimal('0')

            movimientos_a_recalcular = self.session.query(MovimientoStock).filter(
                MovimientoStock.producto_id == prod_id,
                MovimientoStock.almacen_id == alm_id,
                MovimientoStock.fecha_documento >= fecha_referencia
            ).order_by(MovimientoStock.fecha_documento.asc(), MovimientoStock.id.asc()).all()

            if not movimientos_a_recalcular:
                continue

            for mov in movimientos_a_recalcular:
                cant_entrada = Decimal(str(mov.cantidad_entrada))
                cant_salida = Decimal(str(mov.cantidad_salida))
                costo_total_movimiento = Decimal(str(mov.costo_total))

                costo_promedio_anterior = Decimal('0')
                if saldo_cant_actual > 0:
                    costo_promedio_anterior = (saldo_costo_actual / saldo_cant_actual).quantize(SEIS_DECIMALES, rounding=ROUND_HALF_UP)

                if cant_salida > 0:
                    costo_unitario_salida = costo_promedio_anterior
                    costo_total_salida = (cant_salida * costo_unitario_salida).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                    mov.costo_unitario = float(costo_unitario_salida)
                    mov.costo_total = float(costo_total_salida)
                    costo_total_movimiento = -costo_total_salida
                elif cant_entrada > 0:
                    costo_total_movimiento = Decimal(str(mov.costo_total))
                else:
                    costo_total_movimiento = Decimal('0')

                saldo_cant_actual += cant_entrada - cant_salida
                saldo_costo_actual += costo_total_movimiento

                if saldo_cant_actual <= 0:
                    saldo_costo_actual = Decimal('0')
                    saldo_cant_actual = Decimal('0')

                mov.saldo_cantidad = float(saldo_cant_actual.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP))
                mov.saldo_costo_total = float(saldo_costo_actual.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP))

            print(f"DEBUG: Recálculo completado para Producto ID: {prod_id}, Almacén ID: {alm_id}")

        print(f"DEBUG: Recálculo de Kardex finalizado.")

    def cargar_compras(self):
        """Carga las compras usando una nueva sesión y filtros de periodo contable."""

        mes_sel = self.cmb_mes_filtro.currentData()
        anio_sel = app_context.get_selected_year()

        primer_dia, num_dias = calendar.monthrange(anio_sel, mes_sel)
        fecha_desde = date(anio_sel, mes_sel, 1)
        fecha_hasta = date(anio_sel, mes_sel, num_dias)

        print(f"DEBUG: Cargando periodo contable: {fecha_desde} al {fecha_hasta}")

        prov_id = self.cmb_proveedor_filtro.currentData()

        temp_session = obtener_session()
        compras = []
        try:
            columna_fecha_filtro = func.coalesce(Compra.fecha_registro_contable, Compra.fecha)

            query = temp_session.query(Compra).options(
                joinedload(Compra.proveedor)
            )

            query = query.filter(
                columna_fecha_filtro >= fecha_desde,
                columna_fecha_filtro <= fecha_hasta
            )

            if prov_id:
                query = query.filter_by(proveedor_id=prov_id)

            compras = query.order_by(columna_fecha_filtro.asc(), Compra.id.asc()).all()

            print(f"DEBUG (cargar_compras POST-QUERY): Se leyeron {len(compras)} compras.")
            for c in compras:
                print(f"  -> Leyendo Compra ID {c.id}: Total={c.total}, F.Emisión={c.fecha}, F.Contable={c.fecha_registro_contable}")

        except Exception as e:
             QMessageBox.critical(self, "Error al Cargar Compras", f"No se pudieron cargar los datos:\n{e}")
             print(f"ERROR en cargar_compras: {e}")
             import traceback
             traceback.print_exc()
        finally:
             temp_session.close()
             print("DEBUG: Sesión temporal cerrada en cargar_compras.")

        self.mostrar_compras(compras)

    def mostrar_compras(self, compras):
        """Muestra compras en la tabla, convirtiendo a Soles si es necesario."""

        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "F. Contable", "F. Emisión", "Documento", "Proveedor", "Moneda", "Subtotal", "IGV", "Total", "Acciones"
        ])
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Proveedor
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed) # Acciones
        self.tabla.setColumnWidth(0, 90)
        self.tabla.setColumnWidth(1, 90)
        self.tabla.setColumnWidth(8, 160)

        self.tabla.setRowCount(len(compras))

        total_soles_calculado = Decimal('0')
        vista_seleccionada = self.cmb_vista_moneda.currentData()

        for row, compra in enumerate(compras):

            subtotal_orig = Decimal(str(getattr(compra, 'subtotal', '0')))
            igv_orig = Decimal(str(getattr(compra, 'igv', '0')))
            total_orig = Decimal(str(getattr(compra, 'total', '0')))
            tc = Decimal(str(getattr(compra, 'tipo_cambio', '1.0')))
            DOS_DECIMALES = Decimal('0.01')
            moneda_simbolo_mostrar = "S/"
            if vista_seleccionada == 'SOLES':
                if compra.moneda == Moneda.DOLARES:
                    subtotal_mostrar = (subtotal_orig * tc).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                    igv_mostrar = (igv_orig * tc).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                    total_mostrar = (total_orig * tc).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                else:
                    subtotal_mostrar = subtotal_orig
                    igv_mostrar = igv_orig
                    total_mostrar = total_orig
                moneda_simbolo_mostrar = "S/"
            else:
                subtotal_mostrar = subtotal_orig
                igv_mostrar = igv_orig
                total_mostrar = total_orig
                moneda_simbolo_mostrar = "S/" if compra.moneda == Moneda.SOLES else "$"

            # Col 0: F. Contable
            f_contable = getattr(compra, 'fecha_registro_contable', None)
            f_contable_str = f_contable.strftime('%d/%m/%Y') if f_contable else "--"
            self.tabla.setItem(row, 0, QTableWidgetItem(f_contable_str))

            # Col 1: F. Emisión
            self.tabla.setItem(row, 1, QTableWidgetItem(compra.fecha.strftime('%d/%m/%Y')))

            # Col 2: Documento
            self.tabla.setItem(row, 2, QTableWidgetItem(f"{compra.tipo_documento.value} {compra.numero_documento}"))

            # Col 3: Proveedor
            proveedor_nombre = "Proveedor Desconocido"
            if compra.proveedor:
                 try:
                      proveedor_nombre = compra.proveedor.razon_social
                 except Exception as prov_err:
                      print(f"ADVERTENCIA: No se pudo acceder a proveedor.razon_social para Compra ID {compra.id}: {prov_err}")
            self.tabla.setItem(row, 3, QTableWidgetItem(proveedor_nombre))

            # Col 4: Moneda
            self.tabla.setItem(row, 4, QTableWidgetItem(moneda_simbolo_mostrar))
            # Col 5: Subtotal
            self.tabla.setItem(row, 5, QTableWidgetItem(f"{moneda_simbolo_mostrar} {subtotal_mostrar:.2f}"))
            # Col 6: IGV
            self.tabla.setItem(row, 6, QTableWidgetItem(f"{moneda_simbolo_mostrar} {igv_mostrar:.2f}"))
            # Col 7: Total
            self.tabla.setItem(row, 7, QTableWidgetItem(f"{moneda_simbolo_mostrar} {total_mostrar:.2f}"))

            if compra.moneda == Moneda.DOLARES:
                 total_soles_calculado += (total_orig * tc)
            else:
                 total_soles_calculado += total_orig

            botones_layout = QHBoxLayout()
            botones_layout.setContentsMargins(0, 0, 0, 0)
            botones_layout.setSpacing(5)

            btn_ver = QPushButton("👁️ Ver")
            btn_ver.setStyleSheet("QPushButton { background-color: #1a73e8; color: white; padding: 5px; border-radius: 3px; } QPushButton:hover { background-color: #1e88e5; }")
            btn_ver.clicked.connect(lambda checked, c=compra: self.ver_detalle(c))
            botones_layout.addWidget(btn_ver)

            btn_editar = QPushButton("✏️ Editar")
            btn_editar.setStyleSheet("QPushButton { background-color: #fbbc04; color: white; padding: 5px; border-radius: 3px; } QPushButton:hover { background-color: #fdd835; }")
            btn_editar.clicked.connect(lambda checked, c=compra: self.editar_compra(c))
            if self.user_info and self.user_info.get('licencia_vencida'):
                 btn_editar.setEnabled(False)
            botones_layout.addWidget(btn_editar)

            btn_eliminar = QPushButton("🗑️ Eliminar")
            btn_eliminar.setStyleSheet("QPushButton { background-color: #ea4335; color: white; padding: 5px; border-radius: 3px; } QPushButton:hover { background-color: #e57373; }")
            btn_eliminar.clicked.connect(lambda checked, c=compra: self.eliminar_compra(c))
            if self.user_info and self.user_info.get('licencia_vencida'):
                 btn_eliminar.setEnabled(False)
            botones_layout.addWidget(btn_eliminar)

            botones_layout.addStretch()
            botones_widget = QWidget()
            botones_widget.setLayout(botones_layout)

            self.tabla.setCellWidget(row, 8, botones_widget)

        self.lbl_contador.setText(f"📊 Total: {len(compras)} compra(s) | Total en soles: S/ {total_soles_calculado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}")

    def nueva_compra(self):
        """Abre diálogo para nueva compra"""
        dialog = CompraDialog(self, self.user_info)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_compras()

    def ver_detalle(self, compra_stale):
        """Muestra el detalle actualizado de la compra en un nuevo diálogo."""
        try:
            self.session.expire_all()
            print(f"DEBUG: Sesión expirada en ver_detalle para Compra ID {compra_stale.id}")

            compra_actualizada = self.session.get(Compra, compra_stale.id)
            if not compra_actualizada:
                 QMessageBox.critical(self, "Error Fatal", f"No se encontró la compra con ID {compra_stale.id} después de refrescar.")
                 return
            print(f"DEBUG: Compra ID {compra_actualizada.id} re-obtenida para detalle. Subtotal: {compra_actualizada.subtotal}")

            detalles = self.session.query(CompraDetalle).filter_by(compra_id=compra_actualizada.id).all()

            dialog = DetalleCompraDialog(compra_actualizada, detalles, self.session, self)
            dialog.exec()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error al ver detalle", f"No se pudo cargar el detalle:\n{e}")
            import traceback
            traceback.print_exc()

    def eliminar_compra(self, compra_a_eliminar):
        """
        Elimina una compra, sus detalles y movimientos de stock asociados,
        y luego recalcula el Kardex.
        """

        confirmar = QMessageBox.warning(self, "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar permanentemente la compra:\n\n"
            f"Documento: {compra_a_eliminar.numero_documento}\n"
            f"Proveedor: {compra_a_eliminar.proveedor.razon_social}\n"
            f"Total: {compra_a_eliminar.total:.2f}\n\n"
            f"Esta acción eliminará los movimientos de Kardex asociados y recalculará los saldos. Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirmar == QMessageBox.StandardButton.No:
            return

        producto_almacen_afectados = set()
        fecha_compra = compra_a_eliminar.fecha
        numero_doc_original = compra_a_eliminar.numero_documento
        tipo_doc_original = compra_a_eliminar.tipo_documento
        compra_id = compra_a_eliminar.id

        try:
            compra = self.session.get(Compra, compra_id)
            if not compra:
                 raise Exception("La compra ya no existe o no se pudo cargar en la sesión.")

            detalles = self.session.query(CompraDetalle).filter_by(compra_id=compra.id).all()

            print(f"DEBUG (Eliminar): Eliminando {len(detalles)} detalles y sus movimientos...")

            for det in detalles:
                producto_almacen_afectados.add((det.producto_id, det.almacen_id))

                mov_original = self.session.query(MovimientoStock).filter_by(
                    tipo=TipoMovimiento.COMPRA,
                    tipo_documento=tipo_doc_original,
                    numero_documento=numero_doc_original,
                    producto_id=det.producto_id,
                    almacen_id=det.almacen_id
                ).first()

                if mov_original:
                    print(f"DEBUG (Eliminar): Eliminando MovimientoStock ID {mov_original.id}")
                    self.session.delete(mov_original)
                else:
                    print(f"ADVERTENCIA (Eliminar): No se encontró MovimientoStock para el detalle {det.id}")

                self.session.delete(det)

            print(f"DEBUG (Eliminar): Eliminando Compra ID {compra.id}")
            self.session.delete(compra)

            self.session.flush()

            if producto_almacen_afectados:
                print(f"DEBUG (Eliminar): Recalculando Kardex para {producto_almacen_afectados} desde {fecha_compra}")
                self.recalcular_kardex_posterior(producto_almacen_afectados, fecha_compra)

            self.session.commit()

            QMessageBox.information(self, "Éxito", "Compra eliminada y Kardex recalculado exitosamente.")

            self.cargar_compras()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error al Eliminar", f"No se pudo eliminar la compra:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def editar_compra(self, compra):
        """Abre el diálogo para editar una compra existente."""
        try:
            # Cargar detalles originales (CORREGIDO: permitir lista vacía)
            detalles_originales = self.session.query(CompraDetalle).filter_by(compra_id=compra.id).all()

            # (Se eliminó el 'if not detalles_originales' que bloqueaba la edición)

            dialog = CompraDialog(parent=self, user_info=self.user_info, compra_a_editar=compra, detalles_originales=detalles_originales)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                import time
                print("DEBUG: Pausa de 0.2s antes de recargar...")
                time.sleep(0.2)

                self.cargar_compras()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error al Cargar Edición", f"No se pudo cargar la compra para editar:\n{str(e)}")
            import traceback
            traceback.print_exc()

# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    ventana = ComprasWindow()
    ventana.resize(1200, 700)
    ventana.show()
    sys.exit(app.exec())
