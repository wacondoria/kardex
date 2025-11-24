"""
Gestión de Ventas - Sistema Kardex Valorizado
Archivo: src/views/ventas_window.py
(Refactorizado para coincidir con la arquitectura de ComprasWindow)
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox,
                             QTextEdit, QCheckBox, QMessageBox, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QSpinBox,
                             QSizePolicy, QFileDialog)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QFont, QKeyEvent
import sys
import calendar
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import joinedload
from sqlalchemy import func, extract

sys.path.insert(0, str(Path(__file__).parent.parent))

# --- IMPORTACIÓN DE DIÁLOGOS MAESTROS ---
from .productos_window import ProductoDialog
try:
    from .clientes_window import ClienteDialog
except ImportError:
    print("ADVERTENCIA: No se encontró 'clientes_window.py'. El botón 'Nuevo Cliente' no funcionará.")
    ClienteDialog = None
# --- FIN DE IMPORTACIONES ---

from models.database_model import (obtener_session, Venta, VentaDetalle,
                                   Cliente, Producto, Almacen, Empresa,
                                   TipoCambio, TipoDocumento, Moneda,
                                   MovimientoStock, TipoMovimiento)
from utils.widgets import UppercaseValidator, SearchableComboBox, MoneyDelegate
from utils.app_context import app_context
from utils.validation import verificar_estado_anio, AnioCerradoError
from utils.button_utils import style_button
from utils.kardex_manager import KardexManager
from utils.ventas_manager import VentasManager
from utils.styles import STYLE_CUADRADO_VERDE, STYLE_CHECKBOX_CUSTOM

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
        QTimer.singleShot(0, self.selectAll)

# ============================================
# DIÁLOGO DE CREAR/EDITAR VENTA
# ============================================

class VentaDialog(QDialog):
    """Diálogo para registrar y editar ventas"""

    def __init__(self, parent=None, user_info=None, venta_a_editar=None, detalles_originales=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.user_info = user_info
        self.venta_original = venta_a_editar
        self.detalles_originales_obj = detalles_originales
        self.detalles_venta = []
        self.lista_completa_productos = []
        self.ventas_manager = VentasManager(self.session)
        # Mantenemos kardex_manager para consultas directas si hace falta,
        # aunque VentasManager ya lo tiene.
        self.kardex_manager = KardexManager(self.session)

        self.init_ui()
        self.cargar_datos_iniciales()

        if self.venta_original:
            self.cargar_datos_para_edicion()

    def init_ui(self):
        self.setWindowTitle("Registrar Venta")
        self.setMinimumSize(1500, 800)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        titulo = QLabel("📦 Nueva Venta")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)
        
        # === DATOS DE LA VENTA ===
        grupo_venta = QGroupBox("Datos de la Venta")
        form_venta = QFormLayout()
        form_venta.setSpacing(10)
        
        # --- Fila Cliente y Nro. Proceso (Estilo Compras) ---
        layout_fila1_completa = QVBoxLayout()
        layout_fila1_completa.setSpacing(3)
        
        fila_cliente_proceso = QHBoxLayout()
        
        fila_cliente_proceso.addWidget(QLabel("Cliente:*"))
        
        self.cmb_cliente = SearchableComboBox()
        self.cmb_cliente.currentIndexChanged.connect(self.cliente_seleccionado)
        fila_cliente_proceso.addWidget(self.cmb_cliente, 2)
        
        self.btn_nuevo_cliente = QPushButton("+")
        self.btn_nuevo_cliente.setToolTip("Crear nuevo cliente")
        self.btn_nuevo_cliente.setFixedSize(30, 30)
        self.btn_nuevo_cliente.setStyleSheet(STYLE_CUADRADO_VERDE)
        self.btn_nuevo_cliente.clicked.connect(self.crear_nuevo_cliente)
        fila_cliente_proceso.addWidget(self.btn_nuevo_cliente)

        fila_cliente_proceso.addSpacing(15)

        fila_cliente_proceso.addWidget(QLabel("Nro. Proceso:*"))
        
        self.txt_numero_proceso = SelectAllLineEdit()
        self.txt_numero_proceso.setPlaceholderText("Ej: 1 (se autocompletará)")
        self.txt_numero_proceso.setToolTip("Ingrese el correlativo. El formato 05MMNNNNNN se generará automáticamente.")
        fila_cliente_proceso.addWidget(self.txt_numero_proceso, 1)
        
        layout_fila1_completa.addLayout(fila_cliente_proceso)
        
        self.lbl_cliente_info = QLabel()
        self.lbl_cliente_info.setStyleSheet("color: #666; font-size: 10px;")
        layout_fila1_completa.addWidget(self.lbl_cliente_info)

        form_venta.addRow(layout_fila1_completa)
        # --- Fin Fila Cliente ---

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
        self.date_fecha_contable.setToolTip("Fecha de registro para el Periodo Contable")

        self.cmb_tipo_doc = QComboBox()
        # Mismos tipos que en Compras, adaptados a Venta
        self.cmb_tipo_doc.addItem("FACTURA", TipoDocumento.FACTURA.value)
        self.cmb_tipo_doc.addItem("BOLETA", TipoDocumento.BOLETA.value)
        self.cmb_tipo_doc.addItem("NOTA DE VENTA", "NOTA_VENTA") # Asumir tipo

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

        form_venta.addRow("", fila1)

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

        form_venta.addRow("", fila2)

        # IGV
        self.chk_incluye_igv = QCheckBox("Los precios INCLUYEN IGV (18%)")
        self.chk_incluye_igv.setStyleSheet(STYLE_CHECKBOX_CUSTOM)
        self.chk_incluye_igv.toggled.connect(self.recalcular_totales)
        form_venta.addRow("", self.chk_incluye_igv)

        grupo_venta.setLayout(form_venta)
        layout.addWidget(grupo_venta)

        # === PRODUCTOS ===
        grupo_productos = QGroupBox("Productos")
        productos_layout = QVBoxLayout()

        selector_layout = QHBoxLayout()

        self.cmb_producto = SearchableComboBox()
        self.cmb_producto.setMinimumWidth(300)
        self.cmb_producto.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self.btn_nuevo_producto = QPushButton("+")
        self.btn_nuevo_producto.setToolTip("Crear nuevo producto")
        self.btn_nuevo_producto.setFixedSize(30, 30)
        self.btn_nuevo_producto.setStyleSheet(STYLE_CUADRADO_VERDE)
        self.btn_nuevo_producto.clicked.connect(self.crear_nuevo_producto)

        self.cmb_almacen = SearchableComboBox()

        self.spn_cantidad = SelectAllSpinBox()
        self.spn_cantidad.setRange(0.00, 999999)
        self.spn_cantidad.setDecimals(2)
        self.spn_cantidad.setValue(1.00)

        self.spn_precio = SelectAllSpinBox()
        self.spn_precio.setRange(0.00, 999999.99)
        self.spn_precio.setDecimals(2)

        self.btn_agregar = QPushButton()
        style_button(self.btn_agregar, 'add', "Agregar")
        self.btn_agregar.clicked.connect(self.agregar_producto)

        self.cmb_producto.installEventFilter(self)
        self.cmb_almacen.installEventFilter(self)
        self.spn_cantidad.installEventFilter(self)
        self.spn_precio.installEventFilter(self)
        self.btn_agregar.installEventFilter(self)

        selector_layout.addWidget(QLabel("Producto:"))
        selector_layout.addWidget(self.cmb_producto, 3)
        selector_layout.addWidget(self.btn_nuevo_producto)
        selector_layout.addWidget(QLabel("Almacén:"))
        selector_layout.addWidget(self.cmb_almacen, 2)
        selector_layout.addWidget(QLabel("Cant:"))
        selector_layout.addWidget(self.spn_cantidad)
        selector_layout.addWidget(QLabel("Precio:"))
        selector_layout.addWidget(self.spn_precio)
        selector_layout.addWidget(self.btn_agregar)
        productos_layout.addLayout(selector_layout)

        # Tabla de productos
        self.tabla_productos = QTableWidget()
        self.tabla_productos.setColumnCount(6)
        self.tabla_productos.setHorizontalHeaderLabels(
            ["Producto", "Almacén", "Cantidad", "Precio Unit.", "Subtotal", "Acción"]
        )
        header = self.tabla_productos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla_productos.setColumnWidth(5, 80)

        money_delegate = MoneyDelegate(self.tabla_productos)
        self.tabla_productos.setItemDelegateForColumn(2, money_delegate)
        self.tabla_productos.setItemDelegateForColumn(3, money_delegate)
        self.tabla_productos.setItemDelegateForColumn(4, money_delegate)

        productos_layout.addWidget(self.tabla_productos)

        grupo_productos.setLayout(productos_layout)
        layout.addWidget(grupo_productos)

        # === TOTALES (SIN COSTOS ADICIONALES) ===
        totales_layout = QHBoxLayout()
        totales_layout.addStretch() # Mover a la derecha

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
        btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar = QPushButton("Guardar Venta")
        style_button(self.btn_guardar, 'add', "Guardar Venta")
        self.btn_guardar.clicked.connect(self.guardar_venta)
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    # --- INICIO DE MÉTODOS DE LÓGICA (Adaptados de Compras) ---

    def cargar_datos_iniciales(self):
        """Carga clientes, productos y almacenes"""
        # Clientes
        self.cmb_cliente.clear()
        clientes = self.session.query(Cliente).filter_by(activo=True).order_by(Cliente.razon_social_o_nombre).all()
        if not clientes:
            QMessageBox.warning(self, "Sin clientes", "No hay clientes registrados.")
        for cli in clientes:
            self.cmb_cliente.addItem(f"{cli.ruc} - {cli.razon_social_o_nombre}", cli.id)
        self.cmb_cliente.setCurrentIndex(-1)

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
        """Carga almacenes y selecciona el principal por defecto."""
        self.cmb_almacen.clear()
        almacenes = self.session.query(Almacen).join(Empresa).filter(
            Almacen.activo == True, Empresa.activo == True
        ).all()
        if not almacenes: return

        almacen_principal = None
        for alm in almacenes:
            self.cmb_almacen.addItem(
                f"{alm.empresa.razon_social} - {alm.nombre}", alm.id
            )
            if alm.es_principal:
                almacen_principal = alm

        if len(almacenes) == 1:
            self.cmb_almacen.setCurrentIndex(0)
        elif almacen_principal:
            index = self.cmb_almacen.findData(almacen_principal.id)
            if index != -1: self.cmb_almacen.setCurrentIndex(index)
        else:
            self.cmb_almacen.setCurrentIndex(-1)

    def cliente_seleccionado(self):
        """Muestra info del cliente seleccionado"""
        cli_id = self.cmb_cliente.currentData()
        if cli_id:
            cli = self.session.query(Cliente).get(cli_id)
            if cli:
                info = f"📞 {cli.telefono or 'Sin teléfono'}"
                if cli.email: info += f" | ✉️ {cli.email}"
                self.lbl_cliente_info.setText(info)
        else:
            self.lbl_cliente_info.setText("")

    def fecha_cambiada(self):
        self.actualizar_tipo_cambio()

    def moneda_cambiada(self):
        es_dolares = self.cmb_moneda.currentData() == Moneda.DOLARES.value
        self.spn_tipo_cambio.setEnabled(es_dolares)
        if es_dolares:
            self.actualizar_tipo_cambio()
        else:
            self.spn_tipo_cambio.setValue(1.000)
        self.recalcular_totales()

    def actualizar_tipo_cambio(self):
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
        prod_id = self.cmb_producto.currentData()
        alm_id = self.cmb_almacen.currentData()
        cantidad = self.spn_cantidad.value()
        precio = self.spn_precio.value()

        if not prod_id or not alm_id:
            QMessageBox.warning(self, "Error", "Seleccione producto y almacén")
            return
        if cantidad <= 0 or precio < 0:
            QMessageBox.warning(self, "Error", "Cantidad debe ser mayor a cero")
            return

        # --- VERIFICACIÓN DE STOCK (NUEVO) ---
        try:
            # Usar VentasManager para verificar stock
            stock_actual = self.ventas_manager.obtener_stock_actual(prod_id, alm_id)
            stock_en_tabla = sum(
                det['cantidad'] for det in self.detalles_venta 
                if det['producto_id'] == prod_id and det['almacen_id'] == alm_id
            )
            
            if (cantidad + stock_en_tabla) > stock_actual:
                QMessageBox.warning(self, "Stock Insuficiente", 
                    f"No hay stock suficiente.\n\nStock Actual: {stock_actual}\n"
                    f"Solicitado: {cantidad + stock_en_tabla}")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error de Stock", f"No se pudo verificar el stock:\n{e}")
            return
        # --- FIN VERIFICACIÓN ---

        producto = self.session.query(Producto).get(prod_id)
        almacen = self.session.query(Almacen).get(alm_id)

        # Usamos el manager para calcular, aunque aquí es solo para un ítem y es rápido hacerlo local
        # pero mantenemos consistencia si queremos.
        # Sin embargo, agregar_producto es UI interaction, el cálculo final masivo se hace en recalcular_totales.
        # Aquí solo añadimos a la lista.

        detalle = {
            'producto_id': prod_id,
            'producto_nombre': f"{producto.codigo} - {producto.nombre}",
            'almacen_id': alm_id,
            'almacen_nombre': almacen.nombre,
            'cantidad': cantidad,
            'precio_unitario': precio,
            'subtotal': 0.0 # Se calculará en recalcular_totales
        }

        self.detalles_venta.append(detalle)
        # Llamamos a recalcular inmediatamente para llenar el subtotal correcto
        self.recalcular_totales()
        self.actualizar_tabla_productos()

        self.spn_cantidad.setValue(1.00)
        self.spn_precio.setValue(0.00)
        self.cmb_producto.setCurrentIndex(-1)
        self.cmb_producto.lineEdit().clear()
        self.cmb_producto.setFocus()

    def actualizar_tabla_productos(self):
        self.tabla_productos.blockSignals(True)
        self.tabla_productos.setRowCount(len(self.detalles_venta))

        for row, det in enumerate(self.detalles_venta):
            combo_producto = SearchableComboBox(self.tabla_productos)
            for prod in self.lista_completa_productos:
                combo_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)
            
            index_actual = combo_producto.findData(det['producto_id'])
            if index_actual != -1: combo_producto.setCurrentIndex(index_actual)
            
            combo_producto.currentIndexChanged.connect(
                lambda index, r=row: self.producto_en_detalle_editado(index, r)
            )
            self.tabla_productos.setCellWidget(row, 0, combo_producto)

            item_alm = QTableWidgetItem(det['almacen_nombre'])
            item_alm.setFlags(item_alm.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla_productos.setItem(row, 1, item_alm)

            item_cant = QTableWidgetItem(f"{det['cantidad']:,.2f}")
            item_precio = QTableWidgetItem(f"{det['precio_unitario']:,.2f}")
            self.tabla_productos.setItem(row, 2, item_cant)
            self.tabla_productos.setItem(row, 3, item_precio)

            item_subtotal = QTableWidgetItem(f"{det['subtotal']:,.2f}")
            item_subtotal.setFlags(item_subtotal.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla_productos.setItem(row, 4, item_subtotal)

            btn_eliminar = QPushButton("✕")
            btn_eliminar.setStyleSheet("background-color: #ea4335; color: white; border-radius: 3px;")
            btn_eliminar.clicked.connect(lambda checked, r=row: self.eliminar_producto(r))
            self.tabla_productos.setCellWidget(row, 5, btn_eliminar)

        self.tabla_productos.blockSignals(False)
        try:
            self.tabla_productos.cellChanged.disconnect(self.detalle_editado)
        except TypeError: pass
        self.tabla_productos.cellChanged.connect(self.detalle_editado)

    def eliminar_producto(self, row):
        if 0 <= row < len(self.detalles_venta):
            del self.detalles_venta[row]
            self.actualizar_tabla_productos()
            self.recalcular_totales()

    def recalcular_totales(self):
        QTimer.singleShot(0, self._actualizar_calculos_igv)

    def _actualizar_calculos_igv(self):
        # Delegar cálculos al manager
        subtotal, igv, total = self.ventas_manager.calcular_totales(
            self.detalles_venta,
            self.chk_incluye_igv.isChecked(),
            self.cmb_moneda.currentData(),
            self.spn_tipo_cambio.value()
        )

        # Actualizar UI de la tabla con los nuevos subtotales calculados en la lista
        self.tabla_productos.blockSignals(True)
        for row, det in enumerate(self.detalles_venta):
            subtotal_item = self.tabla_productos.item(row, 4)
            if not subtotal_item:
                subtotal_item = QTableWidgetItem()
                subtotal_item.setFlags(subtotal_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tabla_productos.setItem(row, 4, subtotal_item)
            subtotal_item.setText(f"{det['subtotal']:,.2f}")
        self.tabla_productos.blockSignals(False)

        # Actualizar etiquetas de totales
        moneda_simbolo = "S/" if self.cmb_moneda.currentData() == Moneda.SOLES.value else "$"
        self.lbl_subtotal.setText(f"{moneda_simbolo} {subtotal:,.2f}")
        self.lbl_igv.setText(f"{moneda_simbolo} {igv:,.2f}")
        self.lbl_total.setText(f"{moneda_simbolo} {total:,.2f}")

    def guardar_venta(self):
        try:
            if not self.cmb_cliente.currentData():
                QMessageBox.warning(self, "Error", "Seleccione un cliente")
                return

            numero_proceso_correlativo = self.txt_numero_proceso.text().strip()
            if not numero_proceso_correlativo.isdigit():
                QMessageBox.warning(self, "Error", "El Número de Proceso debe ser un número (correlativo).")
                return

            serie = self.txt_serie_doc.text().strip()
            numero = self.txt_numero_doc.text().strip()
            if not serie or not numero:
                QMessageBox.warning(self, "Error", "Debe ingresar la serie y el número del documento")
                return
            numero_documento_completo = f"{serie}-{numero}"

            if not self.detalles_venta:
                QMessageBox.warning(self, "Error", "Agregue al menos un producto")
                return
            
            mes_contable = self.date_fecha_contable.date().month()
            numero_proceso_completo = f"05{mes_contable:02d}{int(numero_proceso_correlativo):06d}"

            # Calcular totales nuevamente por seguridad
            subtotal, igv, total = self.ventas_manager.calcular_totales(
                self.detalles_venta,
                self.chk_incluye_igv.isChecked(),
                self.cmb_moneda.currentData(),
                self.spn_tipo_cambio.value()
            )
            
            # Preparar datos para el manager
            datos_cabecera = {
                'numero_proceso': numero_proceso_completo,
                'cliente_id': self.cmb_cliente.currentData(),
                'fecha': self.date_fecha.date().toPyDate(),
                'fecha_registro_contable': self.date_fecha_contable.date().toPyDate(),
                'tipo_documento': TipoDocumento(self.cmb_tipo_doc.currentData()),
                'numero_documento': numero_documento_completo,
                'moneda': Moneda(self.cmb_moneda.currentData()),
                'tipo_cambio': Decimal(str(self.spn_tipo_cambio.value())),
                'incluye_igv': self.chk_incluye_igv.isChecked(),
                'igv_porcentaje': Decimal('18.0'),
                'subtotal': subtotal,
                'igv': igv,
                'total': total,
                'observaciones': self.txt_observaciones.toPlainText().strip() or None
            }

            es_edicion = self.venta_original is not None
            venta_id = self.venta_original.id if es_edicion else None

            # Delegar guardado al manager
            self.ventas_manager.guardar_venta(datos_cabecera, self.detalles_venta, venta_id)
            
            QMessageBox.information(self, "Éxito", f"Venta {'actualizada' if es_edicion else 'registrada'} exitosamente.")
            self.accept()

        except ValueError as e:
            # Errores de validación de negocio (stock, etc)
            QMessageBox.warning(self, "Advertencia", str(e))
        except AnioCerradoError as e:
            QMessageBox.warning(self, "Operación no permitida", str(e))
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al {'actualizar' if self.venta_original else 'guardar'} venta:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def cargar_datos_para_edicion(self):
        if not self.venta_original: return

        # Bloquear señales para evitar recálculos
        widgets_a_bloquear = [
            self.cmb_cliente, self.date_fecha, self.date_fecha_contable,
            self.cmb_tipo_doc, self.txt_serie_doc, self.txt_numero_doc,
            self.cmb_moneda, self.spn_tipo_cambio, self.chk_incluye_igv,
            self.txt_observaciones, self.tabla_productos
        ]
        signal_states = {widget: widget.signalsBlocked() for widget in widgets_a_bloquear}
        for widget in widgets_a_bloquear: widget.blockSignals(True)

        try:
            self.setWindowTitle(f"✏️ Editando Venta: {self.venta_original.numero_documento}")
            self.btn_guardar.setText("Guardar Cambios")

            if self.venta_original.numero_proceso and len(self.venta_original.numero_proceso) >= 6:
                correlativo = self.venta_original.numero_proceso[-6:]
                self.txt_numero_proceso.setText(str(int(correlativo)))
            else:
                self.txt_numero_proceso.setText("")

            index_cli = self.cmb_cliente.findData(self.venta_original.cliente_id)
            if index_cli != -1: self.cmb_cliente.setCurrentIndex(index_cli)
            
            self.date_fecha.setDate(QDate(self.venta_original.fecha.year, self.venta_original.fecha.month, self.venta_original.fecha.day))
            
            fecha_contable_guardada = getattr(self.venta_original, 'fecha_registro_contable', None)
            if fecha_contable_guardada:
                self.date_fecha_contable.setDate(QDate(fecha_contable_guardada.year, fecha_contable_guardada.month, fecha_contable_guardada.day))
            else:
                self.date_fecha_contable.setDate(self.date_fecha.date())

            index_td = self.cmb_tipo_doc.findData(self.venta_original.tipo_documento.value)
            if index_td != -1: self.cmb_tipo_doc.setCurrentIndex(index_td)

            try:
                serie, numero = self.venta_original.numero_documento.split('-', 1)
                self.txt_serie_doc.setText(serie)
                self.txt_numero_doc.setText(numero)
            except ValueError:
                self.txt_serie_doc.setText("")
                self.txt_numero_doc.setText(self.venta_original.numero_documento)

            index_moneda = self.cmb_moneda.findData(self.venta_original.moneda.value)
            if index_moneda != -1: self.cmb_moneda.setCurrentIndex(index_moneda)
            
            self.moneda_cambiada() # Esto ajustará el TC y la UI
            if self.venta_original.moneda == Moneda.DOLARES:
                self.spn_tipo_cambio.setValue(float(self.venta_original.tipo_cambio))
                self.actualizar_tipo_cambio() # Para actualizar la etiqueta de info

            self.chk_incluye_igv.setChecked(self.venta_original.incluye_igv)
            self.txt_observaciones.setPlainText(self.venta_original.observaciones or "")

            self.detalles_venta = []
            for det_obj in self.detalles_originales_obj:
                producto = self.session.query(Producto).get(det_obj.producto_id)
                almacen = self.session.query(Almacen).get(det_obj.almacen_id)
                if not producto or not almacen: continue

                cantidad_orig = Decimal(str(det_obj.cantidad))
                precio_venta_sin_igv = Decimal(str(det_obj.precio_unitario_sin_igv))
                
                precio_ui = precio_venta_sin_igv
                if self.venta_original.incluye_igv:
                    precio_ui = (precio_ui * Decimal('1.18')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                subtotal_ui_sin_igv = (cantidad_orig * precio_venta_sin_igv).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                detalle_dict = {
                    'producto_id': det_obj.producto_id,
                    'producto_nombre': f"{producto.codigo} - {producto.nombre}",
                    'almacen_id': det_obj.almacen_id,
                    'almacen_nombre': almacen.nombre,
                    'cantidad': float(cantidad_orig),
                    'precio_unitario': float(precio_ui),
                    'subtotal': float(subtotal_ui_sin_igv), # El subtotal ya está sin IGV
                    'detalle_original_id': det_obj.id
                }
                self.detalles_venta.append(detalle_dict)

            self.actualizar_tabla_productos()

        finally:
            for widget, original_state in signal_states.items():
                widget.blockSignals(original_state)

        self.recalcular_totales()

    def producto_en_detalle_editado(self, combo_index, row):
        if 0 <= row < len(self.detalles_venta):
            combo_box = self.tabla_productos.cellWidget(row, 0)
            if not combo_box: return
            
            nuevo_producto_id = combo_box.itemData(combo_index)
            nuevo_producto_nombre = combo_box.itemText(combo_index)
            
            if nuevo_producto_id is not None:
                detalle_actualizado = self.detalles_venta[row]
                detalle_actualizado['producto_id'] = nuevo_producto_id
                detalle_actualizado['producto_nombre'] = nuevo_producto_nombre

    def detalle_editado(self, row, column):
        if column not in [2, 3]: return
        item = self.tabla_productos.item(row, column)
        if not item: return
        # Eliminar comas (separador de miles) antes de convertir
        nuevo_valor_str = item.text().replace(',', '')

        try:
            nuevo_valor = float(nuevo_valor_str)
            if nuevo_valor < 0: raise ValueError("Valor no puede ser negativo")
        except ValueError:
            QMessageBox.warning(self, "Valor inválido", f"Ingrese un número válido.")
            self.tabla_productos.blockSignals(True)
            if column == 2: item.setText(f"{self.detalles_venta[row]['cantidad']:,.2f}")
            else: item.setText(f"{self.detalles_venta[row]['precio_unitario']:,.2f}")
            self.tabla_productos.blockSignals(False)
            return

        detalle_actualizado = self.detalles_venta[row]
        if column == 2:
            detalle_actualizado['cantidad'] = nuevo_valor
        else:
            detalle_actualizado['precio_unitario'] = nuevo_valor

        self.recalcular_totales() # Llama a _actualizar_calculos_igv

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
                    if self.cmb_producto.completer.popup().isVisible(): return super().eventFilter(source, event)
                    self.cmb_almacen.setFocus()
                    return True
                elif source is self.cmb_almacen:
                    if hasattr(self.cmb_almacen, 'completer') and self.cmb_almacen.completer and self.cmb_almacen.completer.popup().isVisible(): return super().eventFilter(source, event)
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

    def crear_nuevo_cliente(self):
        if ClienteDialog is None:
            QMessageBox.critical(self, "Error", "El módulo de clientes no se pudo cargar.")
            return
        
        dialog = ClienteDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            texto_actual = self.cmb_cliente.lineEdit().text()
            self.cmb_cliente.clear()
            clientes = self.session.query(Cliente).filter_by(activo=True).order_by(Cliente.razon_social).all()
            for cli in clientes:
                self.cmb_cliente.addItem(f"{cli.ruc} - {cli.razon_social}", cli.id)
            self.cmb_cliente.lineEdit().setText(texto_actual)
            
            if hasattr(dialog, 'nuevo_cliente_id') and dialog.nuevo_cliente_id:
                index = self.cmb_cliente.findData(dialog.nuevo_cliente_id)
                if index != -1: self.cmb_cliente.setCurrentIndex(index)

    def crear_nuevo_producto(self):
        dialog = ProductoDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            nuevo_id = dialog.nuevo_producto_id
            self.cmb_producto.clear()
            self.lista_completa_productos = self.session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
            for prod in self.lista_completa_productos:
                self.cmb_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)
            if nuevo_id:
                index = self.cmb_producto.findData(nuevo_id)
                if index != -1:
                    self.cmb_producto.setCurrentIndex(index)
                    self.cmb_almacen.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4: self.guardar_venta()
        else: super().keyPressEvent(event)

# ============================================
# DIÁLOGO DE VER DETALLE
# ============================================

class DetalleVentaDialog(QDialog):
    """Diálogo de solo lectura para mostrar el detalle de una venta."""
    def __init__(self, venta, detalles, session, parent=None):
        super().__init__(parent)
        self.venta = venta
        self.detalles = detalles
        self.session = session
        self.setWindowTitle(f"Detalle: {venta.tipo_documento.value} {venta.numero_documento}")
        self.setMinimumSize(800, 600)

        self.lbl_subtotal_detalle = None
        self.lbl_igv_detalle = None
        self.lbl_total_detalle = None

        self.init_ui()
        self.recalcular_totales_locales()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15); layout.setSpacing(10)

        grupo_datos = QGroupBox("Datos Generales")
        form_datos = QFormLayout()
        form_datos.addRow(QLabel("<b>Cliente:</b>"), QLabel(self.venta.cliente.razon_social_o_nombre))
        form_datos.addRow(QLabel("<b>Fecha Emisión:</b>"), QLabel(self.venta.fecha.strftime('%d/%m/%Y')))
        
        f_contable_str = self.venta.fecha_registro_contable.strftime('%d/%m/%Y') if getattr(self.venta, 'fecha_registro_contable', None) else "--"
        form_datos.addRow(QLabel("<b>Fecha Contable:</b>"), QLabel(f_contable_str))
        
        form_datos.addRow(QLabel("<b>Documento:</b>"), QLabel(f"{self.venta.tipo_documento.value} {self.venta.numero_documento}"))
        moneda_str = f"{self.venta.moneda.value} (TC: {self.venta.tipo_cambio:.3f})" if self.venta.moneda == Moneda.DOLARES else "SOLES (S/)"
        form_datos.addRow(QLabel("<b>Moneda:</b>"), QLabel(moneda_str))
        igv_str = "Precios INCLUYEN IGV" if self.venta.incluye_igv else "Precios NO incluyen IGV"
        form_datos.addRow(QLabel("<b>Condición:</b>"), QLabel(igv_str))
        if self.venta.observaciones:
            form_datos.addRow(QLabel("<b>Obs:</b>"), QLabel(self.venta.observaciones))
        grupo_datos.setLayout(form_datos)
        layout.addWidget(grupo_datos)

        layout.addWidget(QLabel("<b>Productos:</b>"))
        tabla = QTableWidget()
        tabla.setColumnCount(7)
        tabla.setHorizontalHeaderLabels(["Producto", "Almacén", "Cantidad", "P. Venta (s/IGV)", "Subtotal Venta", "Costo Unit. (Kardex)", "Costo Total (Kardex)"])
        tabla.setRowCount(len(self.detalles))
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for row, det in enumerate(self.detalles):
            producto = self.session.query(Producto).get(det.producto_id)
            almacen = self.session.query(Almacen).get(det.almacen_id)
            producto_nombre = f"{producto.codigo} - {producto.nombre}" if producto else "N/A"
            almacen_nombre = almacen.nombre if almacen else "N/A"

            tabla.setItem(row, 0, QTableWidgetItem(producto_nombre))
            tabla.setItem(row, 1, QTableWidgetItem(almacen_nombre))
            tabla.setItem(row, 2, QTableWidgetItem(f"{det.cantidad:,.2f}"))
            tabla.setItem(row, 3, QTableWidgetItem(f"{det.precio_unitario_sin_igv:,.2f}"))
            tabla.setItem(row, 4, QTableWidgetItem(f"{det.subtotal:,.2f}"))
            tabla.setItem(row, 5, QTableWidgetItem(f"{det.costo_unitario_kardex:.4f}")) # Más decimales para costo
            tabla.setItem(row, 6, QTableWidgetItem(f"{det.costo_total_kardex:,.2f}"))

        tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tabla.resizeColumnsToContents()

        money_delegate_det = MoneyDelegate(tabla)
        tabla.setItemDelegateForColumn(2, money_delegate_det)
        tabla.setItemDelegateForColumn(3, money_delegate_det)
        tabla.setItemDelegateForColumn(4, money_delegate_det)
        tabla.setItemDelegateForColumn(5, money_delegate_det)
        tabla.setItemDelegateForColumn(6, money_delegate_det)

        layout.addWidget(tabla)

        grupo_totales = QGroupBox("Resumen de Totales (Venta)")
        form_totales = QFormLayout()
        simbolo = "$" if self.venta.moneda == Moneda.DOLARES else "S/"

        self.lbl_subtotal_detalle = QLabel(f"{simbolo} --.--")
        form_totales.addRow(QLabel("<b>Subtotal Venta:</b>"), self.lbl_subtotal_detalle)
        self.lbl_igv_detalle = QLabel(f"{simbolo} --.--")
        form_totales.addRow(QLabel("<b>IGV (18%):</b>"), self.lbl_igv_detalle)
        self.lbl_total_detalle = QLabel(f"{simbolo} --.--")
        self.lbl_total_detalle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a73e8;")
        form_totales.addRow(QLabel("<b>TOTAL VENTA:</b>"), self.lbl_total_detalle)

        grupo_totales.setLayout(form_totales)
        grupo_totales.setMaximumWidth(350)
        totales_layout = QHBoxLayout()
        totales_layout.addStretch()
        totales_layout.addWidget(grupo_totales)
        layout.addLayout(totales_layout)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

    def recalcular_totales_locales(self):
        subtotal_real = Decimal(str(getattr(self.venta, 'subtotal', '0')))
        igv_real = Decimal(str(getattr(self.venta, 'igv', '0')))
        total_real = Decimal(str(getattr(self.venta, 'total', '0')))
        simbolo = "$" if self.venta.moneda == Moneda.DOLARES else "S/"
        self.lbl_subtotal_detalle.setText(f"{simbolo} {subtotal_real:,.2f}")
        self.lbl_igv_detalle.setText(f"{simbolo} {igv_real:,.2f}")
        self.lbl_total_detalle.setText(f"{simbolo} {total_real:,.2f}")

# ============================================
# VENTANA PRINCIPAL DE VENTAS
# ============================================

class VentasWindow(QWidget):
    """Ventana principal de ventas"""
    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.ventas_mostradas = []
        self.kardex_manager = KardexManager(self.session)
        self.init_ui()
        self.cargar_ventas()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2: self.nueva_venta()
        elif event.key() == Qt.Key.Key_F6:
            fila = self.tabla.currentRow()
            if fila != -1 and fila < len(self.ventas_mostradas):
                self.editar_venta(self.ventas_mostradas[fila])
        else:
            super().keyPressEvent(event)

    def init_ui(self):
        self.setWindowTitle("Gestión de Ventas")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(15)

        header_layout = QHBoxLayout()
        titulo = QLabel("📦 Gestión de Ventas")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        btn_nueva = QPushButton()
        style_button(btn_nueva, 'add', "Nueva Venta (F2)")
        btn_nueva.clicked.connect(self.nueva_venta)
        if self.user_info and self.user_info.get('licencia_vencida'):
            btn_nueva.setEnabled(False)
            btn_nueva.setToolTip("Licencia vencida - Solo consulta")
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nueva)

        # Filtros (Estilo Compras)
        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("<b>Periodo Contable:</b>"))
        self.cmb_mes_filtro = SearchableComboBox()
        meses_espanol = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        mes_actual = datetime.now().month
        for i, mes in enumerate(meses_espanol):
            self.cmb_mes_filtro.addItem(mes, i + 1)
        self.cmb_mes_filtro.setCurrentIndex(mes_actual - 1)
        self.cmb_mes_filtro.currentIndexChanged.connect(self.cargar_ventas)

        self.cmb_cliente_filtro = SearchableComboBox()
        self.cmb_cliente_filtro.addItem("Todos los clientes", None)
        self.cmb_cliente_filtro.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_cliente_filtro.currentIndexChanged.connect(self.cargar_ventas)
        
        self.cmb_vista_moneda = QComboBox()
        self.cmb_vista_moneda.setFixedWidth(180)
        self.cmb_vista_moneda.addItem("Ver en Moneda de Origen", "ORIGEN")
        self.cmb_vista_moneda.addItem("Mostrar Todo en SOLES (S/)", "SOLES")
        self.cmb_vista_moneda.currentIndexChanged.connect(self.cargar_ventas)

        filtro_layout.addWidget(self.cmb_mes_filtro)
        filtro_layout.addWidget(self.cmb_cliente_filtro)
        filtro_layout.addWidget(self.cmb_vista_moneda)
        filtro_layout.addStretch()
        
        # Recargar filtro de clientes
        self.recargar_filtro_clientes()

        self.lbl_contador = QLabel("Cargando...")
        self.lbl_contador.setStyleSheet("color: #666; font-size: 11px;")

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(10)
        self.tabla.setHorizontalHeaderLabels(
            ["Nro. Proceso", "F. Contable", "F. Emisión", "Documento", "Cliente", "Moneda", "Subtotal", "IGV", "Total", "Acciones"]
        )
        # Se elimina el stylesheet explícito para que herede el tema global (gris/plomo) igual que Compras
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(0, 100); self.tabla.setColumnWidth(1, 90)
        self.tabla.setColumnWidth(2, 90); self.tabla.setColumnWidth(9, 160)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        money_delegate_main = MoneyDelegate(self.tabla)
        self.tabla.setItemDelegateForColumn(6, money_delegate_main)
        self.tabla.setItemDelegateForColumn(7, money_delegate_main)
        self.tabla.setItemDelegateForColumn(8, money_delegate_main)

        layout.addLayout(header_layout)
        layout.addLayout(filtro_layout)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)
        self.setLayout(layout)

    def recargar_filtro_clientes(self):
        """Recarga el combo de filtro de clientes."""
        self.cmb_cliente_filtro.blockSignals(True)
        texto_actual = self.cmb_cliente_filtro.currentText()
        self.cmb_cliente_filtro.clear()
        self.cmb_cliente_filtro.addItem("Todos los clientes", None)
        
        anio_sel = app_context.get_selected_year()
        clientes = self.session.query(Cliente).join(Venta).filter(
            Cliente.activo==True,
            extract('year', Venta.fecha) == anio_sel
        ).distinct().order_by(Cliente.razon_social_o_nombre).all()
        
        for cli in clientes:
            self.cmb_cliente_filtro.addItem(cli.razon_social_o_nombre, cli.id)
        
        self.cmb_cliente_filtro.setCurrentText(texto_actual)
        self.cmb_cliente_filtro.blockSignals(False)

    def cargar_ventas(self):
        mes_sel = self.cmb_mes_filtro.currentData()
        anio_sel = app_context.get_selected_year()
        if not mes_sel or not anio_sel: return

        primer_dia, num_dias = calendar.monthrange(anio_sel, mes_sel)
        fecha_desde = date(anio_sel, mes_sel, 1)
        fecha_hasta = date(anio_sel, mes_sel, num_dias)
        
        cli_id = self.cmb_cliente_filtro.currentData()
        temp_session = obtener_session()
        ventas = []
        try:
            columna_fecha_filtro = func.coalesce(Venta.fecha_registro_contable, Venta.fecha)
            query = temp_session.query(Venta).options(joinedload(Venta.cliente))
            query = query.filter(
                columna_fecha_filtro >= fecha_desde,
                columna_fecha_filtro <= fecha_hasta
            )
            if cli_id:
                query = query.filter_by(cliente_id=cli_id)
            ventas = query.order_by(columna_fecha_filtro.asc(), Venta.id.asc()).all()
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar Ventas", f"No se pudieron cargar los datos:\n{e}")
        finally:
            temp_session.close()
        
        self.mostrar_ventas(ventas)

    def mostrar_ventas(self, ventas):
        self.ventas_mostradas = ventas
        self.tabla.setRowCount(len(ventas))
        total_soles_calculado = Decimal('0')
        vista_seleccionada = self.cmb_vista_moneda.currentData()
        DOS_DECIMALES = Decimal('0.01')

        for row, venta in enumerate(ventas):
            subtotal_orig = Decimal(str(getattr(venta, 'subtotal', '0')))
            igv_orig = Decimal(str(getattr(venta, 'igv', '0')))
            total_orig = Decimal(str(getattr(venta, 'total', '0')))
            tc = Decimal(str(getattr(venta, 'tipo_cambio', '1.0')))
            moneda_simbolo_mostrar = "S/"

            if vista_seleccionada == 'SOLES':
                if venta.moneda == Moneda.DOLARES:
                    subtotal_mostrar = (subtotal_orig * tc).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                    igv_mostrar = (igv_orig * tc).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                    total_mostrar = (total_orig * tc).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
                else:
                    subtotal_mostrar, igv_mostrar, total_mostrar = subtotal_orig, igv_orig, total_orig
                moneda_simbolo_mostrar = "S/"
            else:
                subtotal_mostrar, igv_mostrar, total_mostrar = subtotal_orig, igv_orig, total_orig
                moneda_simbolo_mostrar = "S/" if venta.moneda == Moneda.SOLES else "$"

            if venta.moneda == Moneda.DOLARES:
                total_soles_calculado += (total_orig * tc)
            else:
                total_soles_calculado += total_orig

            self.tabla.setItem(row, 0, QTableWidgetItem(venta.numero_proceso or "N/A"))
            f_contable = getattr(venta, 'fecha_registro_contable', None)
            f_contable_str = f_contable.strftime('%d/%m/%Y') if f_contable else "--"
            self.tabla.setItem(row, 1, QTableWidgetItem(f_contable_str))
            self.tabla.setItem(row, 2, QTableWidgetItem(venta.fecha.strftime('%d/%m/%Y')))
            self.tabla.setItem(row, 3, QTableWidgetItem(f"{venta.tipo_documento.value} {venta.numero_documento}"))
            cliente_nombre = venta.cliente.razon_social_o_nombre if venta.cliente else "Cliente Desconocido"
            self.tabla.setItem(row, 4, QTableWidgetItem(cliente_nombre))
            self.tabla.setItem(row, 5, QTableWidgetItem(moneda_simbolo_mostrar))
            self.tabla.setItem(row, 6, QTableWidgetItem(f"{moneda_simbolo_mostrar} {subtotal_mostrar:,.2f}"))
            self.tabla.setItem(row, 7, QTableWidgetItem(f"{moneda_simbolo_mostrar} {igv_mostrar:,.2f}"))
            self.tabla.setItem(row, 8, QTableWidgetItem(f"{moneda_simbolo_mostrar} {total_mostrar:,.2f}"))

            botones_layout = QHBoxLayout(); botones_layout.setContentsMargins(0, 0, 0, 0); botones_layout.setSpacing(5)
            btn_ver = QPushButton(); style_button(btn_ver, 'view', "Ver")
            btn_ver.clicked.connect(lambda checked, c=venta: self.ver_detalle_venta(c))
            botones_layout.addWidget(btn_ver)
            btn_editar = QPushButton(); style_button(btn_editar, 'edit', "Editar (F6)")
            btn_editar.clicked.connect(lambda checked, c=venta: self.editar_venta(c))
            if self.user_info and self.user_info.get('licencia_vencida'): btn_editar.setEnabled(False)
            botones_layout.addWidget(btn_editar)
            btn_eliminar = QPushButton(); style_button(btn_eliminar, 'delete', "Eliminar")
            btn_eliminar.clicked.connect(lambda checked, c=venta: self.eliminar_venta(c))
            if self.user_info and self.user_info.get('licencia_vencida'): btn_eliminar.setEnabled(False)
            botones_layout.addWidget(btn_eliminar)
            botones_layout.addStretch()
            botones_widget = QWidget(); botones_widget.setLayout(botones_layout)
            self.tabla.setCellWidget(row, 9, botones_widget)

        self.lbl_contador.setText(f"📊 Total: {len(ventas)} venta(s) | Total en soles: S/ {total_soles_calculado.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP):,.2f}")

    def nueva_venta(self):
        dialog = VentaDialog(self, self.user_info)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.recargar_filtro_clientes()
            self.cargar_ventas()

    def ver_detalle_venta(self, venta_stale):
        try:
            self.session.expire_all()
            venta_actualizada = self.session.get(Venta, venta_stale.id)
            if not venta_actualizada:
                QMessageBox.critical(self, "Error", "No se encontró la venta.")
                return
            detalles = self.session.query(VentaDetalle).filter_by(venta_id=venta_actualizada.id).all()
            dialog = DetalleVentaDialog(venta_actualizada, detalles, self.session, self)
            dialog.exec()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo cargar el detalle:\n{e}")

    def eliminar_venta(self, venta_a_eliminar):
        confirmar = QMessageBox.warning(self, "Confirmar Eliminación",
            f"¿Está seguro de eliminar la venta:\n\n"
            f"Documento: {venta_a_eliminar.numero_documento}\n"
            f"Cliente: {venta_a_eliminar.cliente.razon_social_o_nombre}\n"
            f"Total: {venta_a_eliminar.total:,.2f}\n\n"
            f"Esta acción anulará los movimientos de Kardex y recalculará los saldos. No se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmar == QMessageBox.StandardButton.No: return

        try:
            self.ventas_manager.eliminar_venta(venta_a_eliminar.id)
            
            QMessageBox.information(self, "Éxito", "Venta eliminada y Kardex recalculado.")
            self.recargar_filtro_clientes()
            self.cargar_ventas()
        
        except AnioCerradoError as e:
            QMessageBox.warning(self, "Operación no permitida", str(e))
            self.session.rollback()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error al Eliminar", f"No se pudo eliminar la venta:\n{str(e)}")

    def editar_venta(self, venta):
        try:
            # Verificar estado del año ANTES de abrir el diálogo
            verificar_estado_anio(venta.fecha_registro_contable or venta.fecha)
            
            detalles_originales = self.session.query(VentaDetalle).filter_by(venta_id=venta.id).all()
            
            dialog = VentaDialog(parent=self, user_info=self.user_info, venta_a_editar=venta, detalles_originales=detalles_originales)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                QTimer.singleShot(200, self.cargar_ventas) # Pequeña pausa para que el recálculo termine
        
        except AnioCerradoError as e:
            QMessageBox.warning(self, "Operación no permitida", str(e))
            self.session.rollback()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error al Cargar Edición", f"No se pudo cargar la venta para editar:\n{str(e)}")

# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Simular user_info para pruebas
    simulated_user_info = {
        'id': 1, 'username': 'test', 'nombre_completo': 'Usuario Prueba',
        'rol': 'ADMINISTRADOR', 'licencia_vencida': False
    }
    
    ventana = VentasWindow(user_info=simulated_user_info)
    ventana.resize(1200, 700)
    ventana.show()
    sys.exit(app.exec())