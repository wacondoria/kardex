"""
Gestión de Ventas - Sistema Kardex Valorizado
Archivo: src/views/ventas_window.py
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

from models.database_model import (obtener_session, Venta, VentaDetalle,
                                   Cliente, Producto, Almacen, Empresa,
                                   TipoCambio, TipoDocumento, Moneda,
                                   SerieCorrelativo, Proyecto)
from utils.ventas_manager import VentasManager, AnioCerradoError
from utils.app_context import app_context
from utils.widgets import SearchableComboBox, MoneyDelegate
from utils.button_utils import style_button
from utils.validation import verificar_estado_anio

# --- IMPORTACIÓN DE DIÁLOGOS MAESTROS ---
from .productos_window import ProductoDialog
try:
    from .clientes_window import ClienteDialog
except ImportError:
    ClienteDialog = None

class VentaDialog(QDialog):
    """Diálogo para Crear o Editar Venta"""
    def __init__(self, parent=None, user_info=None, venta_a_editar=None, detalles_originales=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.user_info = user_info
        self.venta_original = venta_a_editar
        self.detalles_originales_obj = detalles_originales
        self.ventas_manager = VentasManager(self.session)
        self.detalles_venta = [] # Lista de dicts
        self.lista_completa_productos = []

        self.init_ui()
        self.cargar_datos_iniciales()

        if self.venta_original:
            self.cargar_datos_para_edicion()

    def init_ui(self):
        self.setWindowTitle("Nueva Venta" if not self.venta_original else f"Editar Venta {self.venta_original.numero_documento}")
        self.resize(1100, 700)

        layout = QVBoxLayout(self)
        
        # --- CABECERA ---
        grupo_cabecera = QGroupBox("Datos del Documento")
        layout_cabecera = QFormLayout()

        # Fila 1: Cliente y Documento
        row1 = QHBoxLayout()

        self.cmb_doc_cliente = SearchableComboBox()
        self.cmb_doc_cliente.setPlaceholderText("RUC/DNI Cliente")
        self.cmb_doc_cliente.setFixedWidth(150)
        self.cmb_doc_cliente.currentIndexChanged.connect(self.cliente_doc_cambiado)

        self.cmb_nombre_cliente = SearchableComboBox()
        self.cmb_nombre_cliente.setPlaceholderText("Razón Social / Nombre")
        self.cmb_nombre_cliente.currentIndexChanged.connect(self.cliente_nombre_cambiado)

        btn_nuevo_cliente = QPushButton("+")
        btn_nuevo_cliente.setFixedSize(30, 30)
        style_button(btn_nuevo_cliente, 'add', "Nuevo Cliente")
        btn_nuevo_cliente.clicked.connect(self.crear_nuevo_cliente)

        row1.addWidget(QLabel("Cliente:"))
        row1.addWidget(self.cmb_doc_cliente)
        row1.addWidget(self.cmb_nombre_cliente)
        row1.addWidget(btn_nuevo_cliente)

        layout_cabecera.addRow(row1)

        # Fila 2: Fechas y Moneda
        row2 = QHBoxLayout()

        self.date_fecha = QDateEdit(QDate.currentDate())
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.setDisplayFormat("dd/MM/yyyy")

        self.date_fecha_contable = QDateEdit(QDate.currentDate())
        self.date_fecha_contable.setCalendarPopup(True)
        self.date_fecha_contable.setDisplayFormat("dd/MM/yyyy")

        self.cmb_moneda = QComboBox()
        for m in Moneda:
            self.cmb_moneda.addItem(m.value, m)
        self.cmb_moneda.currentIndexChanged.connect(self.moneda_cambiada)

        self.spn_tipo_cambio = QDoubleSpinBox()
        self.spn_tipo_cambio.setDecimals(3)
        self.spn_tipo_cambio.setRange(0.001, 100.0)
        self.spn_tipo_cambio.setValue(1.000)

        self.lbl_info_tc = QLabel("")
        self.lbl_info_tc.setStyleSheet("color: blue; font-size: 10px;")

        row2.addWidget(QLabel("F. Emisión:"))
        row2.addWidget(self.date_fecha)
        row2.addWidget(QLabel("F. Contable:"))
        row2.addWidget(self.date_fecha_contable)
        row2.addWidget(QLabel("Moneda:"))
        row2.addWidget(self.cmb_moneda)
        row2.addWidget(QLabel("T. Cambio:"))
        row2.addWidget(self.spn_tipo_cambio)
        row2.addWidget(self.lbl_info_tc)

        layout_cabecera.addRow(row2)

        # Fila 3: Documento (Tipo, Serie, Numero)
        row3 = QHBoxLayout()

        self.cmb_tipo_doc = QComboBox()
        for td in TipoDocumento:
            self.cmb_tipo_doc.addItem(td.value, td)

        self.txt_serie_doc = QLineEdit()
        self.txt_serie_doc.setPlaceholderText("F001")
        self.txt_serie_doc.setMaxLength(4)

        self.txt_numero_doc = QLineEdit()
        self.txt_numero_doc.setPlaceholderText("00000001")
        self.txt_numero_doc.setMaxLength(8)
        self.txt_numero_doc.editingFinished.connect(self.formatear_numero_documento)

        self.txt_numero_proceso = QLineEdit()
        self.txt_numero_proceso.setPlaceholderText("Correlativo (6 dígitos)")
        self.txt_numero_proceso.setMaxLength(6)

        self.chk_incluye_igv = QCheckBox("Precios Incluyen IGV")
        self.chk_incluye_igv.setChecked(True)
        self.chk_incluye_igv.toggled.connect(self.recalcular_totales)

        row3.addWidget(QLabel("Tipo Doc:"))
        row3.addWidget(self.cmb_tipo_doc)
        row3.addWidget(QLabel("Serie:"))
        row3.addWidget(self.txt_serie_doc)
        row3.addWidget(QLabel("Número:"))
        row3.addWidget(self.txt_numero_doc)
        row3.addWidget(QLabel("Nro. Proceso (05MM...):"))
        row3.addWidget(self.txt_numero_proceso)
        row3.addWidget(self.chk_incluye_igv)

        layout_cabecera.addRow(row3)
        grupo_cabecera.setLayout(layout_cabecera)
        layout.addWidget(grupo_cabecera)

        # --- DETALLES ---
        grupo_detalles = QGroupBox("Detalle de Productos")
        layout_detalles = QVBoxLayout()

        # Controles de ingreso
        layout_input = QHBoxLayout()

        self.cmb_producto = SearchableComboBox()
        self.cmb_producto.setPlaceholderText("Buscar Producto...")
        self.cmb_producto.installEventFilter(self)

        self.cmb_almacen = QComboBox()
        self.cmb_almacen.setFixedWidth(150)
        self.cmb_almacen.installEventFilter(self)

        self.spn_cantidad = QDoubleSpinBox()
        self.spn_cantidad.setRange(0.01, 999999)
        self.spn_cantidad.setDecimals(2)
        self.spn_cantidad.setValue(1.00)
        self.spn_cantidad.installEventFilter(self)

        self.spn_precio = QDoubleSpinBox()
        self.spn_precio.setRange(0.01, 9999999)
        self.spn_precio.setDecimals(2)
        self.spn_precio.setPrefix("P.Unit: ")
        self.spn_precio.installEventFilter(self)

        self.btn_agregar = QPushButton("Agregar")
        style_button(self.btn_agregar, 'add', "Agregar")
        self.btn_agregar.clicked.connect(self.agregar_detalle)
        self.btn_agregar.installEventFilter(self)

        btn_nuevo_prod = QPushButton("+")
        btn_nuevo_prod.setFixedSize(30, 30)
        style_button(btn_nuevo_prod, 'add')
        btn_nuevo_prod.clicked.connect(self.crear_nuevo_producto)

        layout_input.addWidget(QLabel("Prod:"))
        layout_input.addWidget(self.cmb_producto, 2)
        layout_input.addWidget(btn_nuevo_prod)
        layout_input.addWidget(QLabel("Alm:"))
        layout_input.addWidget(self.cmb_almacen)
        layout_input.addWidget(QLabel("Cant:"))
        layout_input.addWidget(self.spn_cantidad)
        layout_input.addWidget(self.spn_precio)
        layout_input.addWidget(self.btn_agregar)

        layout_detalles.addLayout(layout_input)

        # Tabla
        self.tabla_productos = QTableWidget()
        self.tabla_productos.setColumnCount(6)
        self.tabla_productos.setHorizontalHeaderLabels(["Producto", "Almacén", "Cantidad", "P. Unitario", "Subtotal", "Acción"])
        self.tabla_productos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla_productos.setColumnWidth(1, 120)
        self.tabla_productos.setColumnWidth(2, 80)
        self.tabla_productos.setColumnWidth(3, 100)
        self.tabla_productos.setColumnWidth(4, 100)
        self.tabla_productos.setColumnWidth(5, 50)
        self.tabla_productos.cellChanged.connect(self.detalle_editado)

        money_delegate = MoneyDelegate(self.tabla_productos)
        self.tabla_productos.setItemDelegateForColumn(2, money_delegate)
        self.tabla_productos.setItemDelegateForColumn(3, money_delegate)
        self.tabla_productos.setItemDelegateForColumn(4, money_delegate)

        layout_detalles.addWidget(self.tabla_productos)

        # Totales
        layout_totales = QHBoxLayout()
        layout_totales.addStretch()

        form_totales = QFormLayout()
        self.lbl_subtotal = QLabel("0.00")
        self.lbl_igv = QLabel("0.00")
        self.lbl_total = QLabel("0.00")
        self.lbl_total.setStyleSheet("font-weight: bold; font-size: 14px;")

        form_totales.addRow("Subtotal:", self.lbl_subtotal)
        form_totales.addRow("IGV (18%):", self.lbl_igv)
        form_totales.addRow("TOTAL:", self.lbl_total)

        layout_totales.addLayout(form_totales)
        layout_detalles.addLayout(layout_totales)

        grupo_detalles.setLayout(layout_detalles)
        layout.addWidget(grupo_detalles)

        # Observaciones
        layout.addWidget(QLabel("Observaciones:"))
        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setMaximumHeight(60)
        layout.addWidget(self.txt_observaciones)

        # Botones finales
        layout_botones = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar Venta (F4)")
        style_button(self.btn_guardar, 'save', "Guardar Venta")
        self.btn_guardar.clicked.connect(self.guardar_venta)
        self.btn_guardar.setMinimumHeight(40)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)

        layout_botones.addStretch()
        layout_botones.addWidget(btn_cancelar)
        layout_botones.addWidget(self.btn_guardar)

        layout.addLayout(layout_botones)

    def cargar_datos_iniciales(self):
        # Clientes
        clientes = self.session.query(Cliente).filter_by(activo=True).order_by(Cliente.razon_social_o_nombre).all()
        for c in clientes:
            self.cmb_doc_cliente.addItem(c.ruc_o_dni, c.id)
            self.cmb_nombre_cliente.addItem(c.razon_social_o_nombre, c.id)

        # Productos
        self.lista_completa_productos = self.session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
        for p in self.lista_completa_productos:
            self.cmb_producto.addItem(f"{p.codigo} - {p.nombre}", p.id)

        # Almacenes
        almacenes = self.session.query(Almacen).filter_by(activo=True).all()
        for a in almacenes:
            self.cmb_almacen.addItem(a.nombre, a.id)

        # Setear almacén principal por defecto
        alm_princ = next((a for a in almacenes if a.es_principal), None)
        if alm_princ:
            idx = self.cmb_almacen.findData(alm_princ.id)
            if idx != -1: self.cmb_almacen.setCurrentIndex(idx)

        # Si no es edición, setear fecha actual y TC
        if not self.venta_original:
            self.actualizar_tipo_cambio()
            # Sugerir correlativo proceso
            self.sugerir_correlativo_proceso()

    def sugerir_correlativo_proceso(self):
        anio = self.date_fecha_contable.date().year()
        mes = self.date_fecha_contable.date().month()
        prefijo_busqueda = f"05{mes:02d}"

        # Buscar el último usado en este mes/año
        ultimo = self.session.query(Venta.numero_proceso)\
            .filter(Venta.numero_proceso.like(f"{prefijo_busqueda}%"))\
            .order_by(Venta.numero_proceso.desc()).first()

        if ultimo and ultimo[0]:
            try:
                correlativo = int(ultimo[0][4:]) + 1
            except:
                correlativo = 1
        else:
            correlativo = 1

        self.txt_numero_proceso.setText(f"{correlativo:06d}")

    def cliente_doc_cambiado(self, index):
        if index == -1: return
        self.cmb_nombre_cliente.blockSignals(True)
        self.cmb_nombre_cliente.setCurrentIndex(index)
        self.cmb_nombre_cliente.blockSignals(False)

    def cliente_nombre_cambiado(self, index):
        if index == -1: return
        self.cmb_doc_cliente.blockSignals(True)
        self.cmb_doc_cliente.setCurrentIndex(index)
        self.cmb_doc_cliente.blockSignals(False)

    def moneda_cambiada(self):
        if self.cmb_moneda.currentData() == Moneda.SOLES:
            self.spn_tipo_cambio.setValue(1.0)
            self.spn_tipo_cambio.setEnabled(False)
        else:
            self.spn_tipo_cambio.setEnabled(True)
            self.actualizar_tipo_cambio()
        self.recalcular_totales()

    def actualizar_tipo_cambio(self):
        fecha = self.date_fecha.date().toPyDate()
        tc = self.session.query(TipoCambio).filter_by(fecha=fecha, activo=True).first()
        if tc:
            # Para ventas se usa el tipo de cambio venta
            val = tc.precio_venta if hasattr(tc, 'precio_venta') else tc.venta
            self.spn_tipo_cambio.setValue(val)
            self.lbl_info_tc.setText(f"TC Venta al {fecha.strftime('%d/%m')}: {val}")
        else:
            self.lbl_info_tc.setText("No hay TC registrado")

    def agregar_detalle(self):
        prod_id = self.cmb_producto.currentData()
        alm_id = self.cmb_almacen.currentData()
        cantidad = self.spn_cantidad.value()
        precio = self.spn_precio.value()
        
        if not prod_id or not alm_id:
             QMessageBox.warning(self, "Error", "Seleccione producto y almacén")
             return

        if cantidad <= 0:
             QMessageBox.warning(self, "Error", "Cantidad debe ser mayor a cero")
             return

        # --- VERIFICACIÓN DE STOCK ---
        try:
            # Calcular stock actual
            stock_actual = self.ventas_manager.obtener_stock_actual(prod_id, alm_id)

            # Sumar lo que ya está en la tabla (por si agrega el mismo producto dos veces)
            stock_en_tabla = sum(
                det['cantidad'] for det in self.detalles_venta 
                if det['producto_id'] == prod_id and det['almacen_id'] == alm_id
            )
            
            # Si es edición, hay que considerar lo que ya estaba en la venta original para no "doble contar" como consumo
            # Pero stock_actual ya descuenta la venta original porque es stock físico actual.
            # Al editar, VentasManager manejará la reversión lógica, pero para la validación de UI:
            # Stock Disponible Real = Stock Actual (DB) + Cantidad Original en esta Venta (si existe)

            cantidad_original_en_venta = 0
            if self.detalles_originales_obj:
                for det_orig in self.detalles_originales_obj:
                     if det_orig.producto_id == prod_id and det_orig.almacen_id == alm_id:
                         cantidad_original_en_venta += det_orig.cantidad

            stock_disponible_para_venta = stock_actual + cantidad_original_en_venta

            if stock_disponible_para_venta < (stock_en_tabla + cantidad):
                 QMessageBox.warning(self, "Stock Insuficiente",
                                     f"Stock disponible: {stock_disponible_para_venta:,.2f}\n"
                                     f"Cantidad acumulada solicitada: {stock_en_tabla + cantidad:,.2f}")
                 return

            # Agregar detalle
            producto = self.session.query(Producto).get(prod_id)
            almacen = self.session.query(Almacen).get(alm_id)
            
            subtotal = cantidad * precio

            detalle = {
                'producto_id': prod_id,
                'producto_nombre': f"{producto.codigo} - {producto.nombre}",
                'almacen_id': alm_id,
                'almacen_nombre': almacen.nombre,
                'cantidad': cantidad,
                'precio_unitario': precio,
                'subtotal': subtotal
            }
            
            self.detalles_venta.append(detalle)
            self.actualizar_tabla_productos()
            self.recalcular_totales()

            # Limpiar inputs
            self.spn_cantidad.setValue(1.0)
            self.spn_precio.setValue(0.0)
            self.cmb_producto.setFocus()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def actualizar_tabla_productos(self):
        self.tabla_productos.blockSignals(True)
        self.tabla_productos.setRowCount(0)

        for i, det in enumerate(self.detalles_venta):
            self.tabla_productos.insertRow(i)
            
            # Producto (Combo para permitir editar)
            cmb_prod = SearchableComboBox()
            for p in self.lista_completa_productos:
                cmb_prod.addItem(f"{p.codigo} - {p.nombre}", p.id)
            index = cmb_prod.findData(det['producto_id'])
            if index != -1: cmb_prod.setCurrentIndex(index)
            # Conectar señal si se quiere permitir cambiar producto en línea (complejo)
            # Por ahora lo dejamos deshabilitado o simple
            cmb_prod.setEnabled(False) # Bloquear cambio de producto por ahora para simplificar
            self.tabla_productos.setCellWidget(i, 0, cmb_prod)
            
            self.tabla_productos.setItem(i, 1, QTableWidgetItem(det['almacen_nombre']))
            self.tabla_productos.setItem(i, 2, QTableWidgetItem(f"{det['cantidad']:,.2f}"))
            self.tabla_productos.setItem(i, 3, QTableWidgetItem(f"{det['precio_unitario']:,.2f}"))
            self.tabla_productos.setItem(i, 4, QTableWidgetItem(f"{det['subtotal']:,.2f}"))
            
            # Bloquear edición de subtotal y almacen
            self.tabla_productos.item(i, 1).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tabla_productos.item(i, 4).setFlags(Qt.ItemFlag.ItemIsEnabled)

            # Botón eliminar
            btn_del = QPushButton("X")
            btn_del.setStyleSheet("color: red; font-weight: bold;")
            btn_del.clicked.connect(lambda _, row=i: self.eliminar_detalle(row))
            self.tabla_productos.setCellWidget(i, 5, btn_del)

        self.tabla_productos.blockSignals(False)

    def eliminar_detalle(self, row):
        if 0 <= row < len(self.detalles_venta):
            self.detalles_venta.pop(row)
            self.actualizar_tabla_productos()
            self.recalcular_totales()

    def detalle_editado(self, row, column):
        if column not in [2, 3]: return

        item = self.tabla_productos.item(row, column)
        if not item: return

        try:
            valor_str = item.text().replace(',', '')
            valor = float(valor_str)
            if valor < 0: raise ValueError
            
            det = self.detalles_venta[row]
            if column == 2: # Cantidad
                det['cantidad'] = valor
            elif column == 3: # Precio
                det['precio_unitario'] = valor

            det['subtotal'] = det['cantidad'] * det['precio_unitario']
            
            # Reflejar cambios en tabla sin disparar señal recursiva
            self.tabla_productos.blockSignals(True)
            self.tabla_productos.item(row, 4).setText(f"{det['subtotal']:,.2f}")
            self.tabla_productos.blockSignals(False)

            self.recalcular_totales()

        except ValueError:
            pass

    def recalcular_totales(self):
        incluye_igv = self.chk_incluye_igv.isChecked()
        total_acumulado = 0.0
        subtotal_acumulado = 0.0
        igv_acumulado = 0.0

        igv_rate = 0.18

        for det in self.detalles_venta:
            # El precio unitario en la lista es el que ingresó el usuario
            # Si "Incluye IGV", ese precio es Bruto. Si no, es Valor Venta.

            precio_ui = det['precio_unitario']
            cantidad = det['cantidad']
            importe_linea = precio_ui * cantidad

            if incluye_igv:
                # El importe linea es Total
                total_acumulado += importe_linea
            else:
                # El importe linea es Subtotal
                subtotal_acumulado += importe_linea

        if incluye_igv:
            # Desglosar
            # Total = Subtotal * 1.18
            # Subtotal = Total / 1.18
            subtotal_acumulado = total_acumulado / (1 + igv_rate)
            igv_acumulado = total_acumulado - subtotal_acumulado
        else:
            # Agregar IGV
            igv_acumulado = subtotal_acumulado * igv_rate
            total_acumulado = subtotal_acumulado + igv_acumulado

        moneda = "S/" if self.cmb_moneda.currentData() == Moneda.SOLES else "$"
        self.lbl_subtotal.setText(f"{moneda} {subtotal_acumulado:,.2f}")
        self.lbl_igv.setText(f"{moneda} {igv_acumulado:,.2f}")
        self.lbl_total.setText(f"{moneda} {total_acumulado:,.2f}")

    def guardar_venta(self):
        try:
            cliente_id = self.cmb_doc_cliente.currentData()
            if not cliente_id:
                QMessageBox.warning(self, "Error", "Seleccione un cliente")
                return

            numero_proceso_correlativo = self.txt_numero_proceso.text().strip()
            if not numero_proceso_correlativo.isdigit():
                QMessageBox.warning(self, "Error", "El Número de Proceso debe ser numérico.")
                return

            serie = self.txt_serie_doc.text().strip()
            numero = self.txt_numero_doc.text().strip()
            if not serie or not numero:
                QMessageBox.warning(self, "Error", "Ingrese serie y número")
                return
            numero_documento_completo = f"{serie}-{numero}"

            if not self.detalles_venta:
                QMessageBox.warning(self, "Error", "Agregue al menos un producto")
                return
            
            mes_contable = self.date_fecha_contable.date().month()
            # Formato 05 + MM + CORRELATIVO
            numero_proceso_completo = f"05{mes_contable:02d}{int(numero_proceso_correlativo):06d}"

            # Obtener totales finales calculados
            # Hack: parsear los labels o recalcular. Mejor recalcular usando la logica del manager para consistencia
            # Pero el manager pide "totales" calculados.

            # Recalcular limpio
            subtotal_val = Decimal(self.lbl_subtotal.text().split(' ')[1].replace(',', ''))
            igv_val = Decimal(self.lbl_igv.text().split(' ')[1].replace(',', ''))
            total_val = Decimal(self.lbl_total.text().split(' ')[1].replace(',', ''))
            
            datos_cabecera = {
                'numero_proceso': numero_proceso_completo,
                'cliente_id': cliente_id,
                'fecha': self.date_fecha.date().toPyDate(),
                'fecha_registro_contable': self.date_fecha_contable.date().toPyDate(),
                'tipo_documento': self.cmb_tipo_doc.currentData(),
                'numero_documento': numero_documento_completo,
                'moneda': self.cmb_moneda.currentData(),
                'tipo_cambio': Decimal(str(self.spn_tipo_cambio.value())),
                'incluye_igv': self.chk_incluye_igv.isChecked(),
                'igv_porcentaje': Decimal('18.0'),
                'subtotal': subtotal_val,
                'igv': igv_val,
                'total': total_val,
                'observaciones': self.txt_observaciones.toPlainText().strip() or None
            }

            es_edicion = self.venta_original is not None
            venta_id = self.venta_original.id if es_edicion else None

            # Guardar
            self.ventas_manager.guardar_venta(datos_cabecera, self.detalles_venta, venta_id)
            
            QMessageBox.information(self, "Éxito", f"Venta {'actualizada' if es_edicion else 'registrada'} exitosamente.")
            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, "Advertencia", str(e))
        except AnioCerradoError as e:
            QMessageBox.warning(self, "Operación no permitida", str(e))
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def cargar_datos_para_edicion(self):
        if not self.venta_original: return

        # Bloquear señales
        self.blockSignals(True)

        try:
            self.setWindowTitle(f"✏️ Editando Venta: {self.venta_original.numero_documento}")
            self.btn_guardar.setText("Guardar Cambios")

            # Proceso
            if self.venta_original.numero_proceso and len(self.venta_original.numero_proceso) >= 6:
                correlativo = self.venta_original.numero_proceso[-6:]
                self.txt_numero_proceso.setText(str(int(correlativo)))
            else:
                self.txt_numero_proceso.setText("")

            # Cliente
            idx = self.cmb_doc_cliente.findData(self.venta_original.cliente_id)
            self.cmb_doc_cliente.setCurrentIndex(idx)
            # El nombre se actualiza solo por la señal, pero estamos bloqueados? No, solo self.
            # Los combos tienen sus propias señales.
            
            # Fechas
            self.date_fecha.setDate(self.venta_original.fecha)
            if self.venta_original.fecha_registro_contable:
                self.date_fecha_contable.setDate(self.venta_original.fecha_registro_contable)

            # Doc
            idx_td = self.cmb_tipo_doc.findData(self.venta_original.tipo_documento)
            self.cmb_tipo_doc.setCurrentIndex(idx_td)
            
            try:
                serie, numero = self.venta_original.numero_documento.split('-', 1)
                self.txt_serie_doc.setText(serie)
                self.txt_numero_doc.setText(numero)
            except:
                self.txt_numero_doc.setText(self.venta_original.numero_documento)

            # Moneda
            idx_mon = self.cmb_moneda.findData(self.venta_original.moneda)
            self.cmb_moneda.setCurrentIndex(idx_mon)
            self.spn_tipo_cambio.setValue(float(self.venta_original.tipo_cambio))
            
            self.chk_incluye_igv.setChecked(self.venta_original.incluye_igv)
            self.txt_observaciones.setText(self.venta_original.observaciones)

            # Detalles
            self.detalles_venta = []
            for det_obj in self.detalles_originales_obj:
                producto = self.session.query(Producto).get(det_obj.producto_id)
                almacen = self.session.query(Almacen).get(det_obj.almacen_id)
                
                # Reconstruir precio unitario según includes IGV
                # En BD precio_unitario es siempre sin IGV o con?
                # En VentaDetalle: precio_unitario es el que se pactó.
                
                # Asumimos que precio_unitario en Detalle guarda el valor base
                # Pero la logica de recalculo usa el valor UI.

                # Si la venta original incluia IGV, el precio unitario guardado en detalle
                # debería ser coherente.

                det_dict = {
                    'producto_id': det_obj.producto_id,
                    'producto_nombre': f"{producto.codigo} - {producto.nombre}",
                    'almacen_id': det_obj.almacen_id,
                    'almacen_nombre': almacen.nombre,
                    'cantidad': float(det_obj.cantidad),
                    'precio_unitario': float(det_obj.precio_unitario), # Precio tal cual se ingresó
                    'subtotal': float(det_obj.subtotal),
                    'detalle_original_id': det_obj.id
                }
                self.detalles_venta.append(det_dict)

            self.actualizar_tabla_productos()
            self.recalcular_totales()

        finally:
            self.blockSignals(False)

    def formatear_numero_documento(self):
        txt = self.txt_numero_doc.text()
        if txt.isdigit():
            self.txt_numero_doc.setText(txt.zfill(8))

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if source == self.cmb_producto:
                     self.cmb_almacen.setFocus()
                     return True
                elif source == self.cmb_almacen:
                     self.spn_cantidad.setFocus()
                     return True
                elif source == self.spn_cantidad:
                     self.spn_precio.setFocus()
                     return True
                elif source == self.spn_precio:
                     self.btn_agregar.click()
                     return True
                elif source == self.btn_agregar:
                     self.cmb_producto.setFocus()
                     return True
        return super().eventFilter(source, event)

    def crear_nuevo_cliente(self):
        if ClienteDialog:
            dlg = ClienteDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                # Recargar clientes
                self.cmb_doc_cliente.clear()
                self.cmb_nombre_cliente.clear()
                clientes = self.session.query(Cliente).filter_by(activo=True).order_by(Cliente.razon_social_o_nombre).all()
                for c in clientes:
                    self.cmb_doc_cliente.addItem(c.ruc_o_dni, c.id)
                    self.cmb_nombre_cliente.addItem(c.razon_social_o_nombre, c.id)
                # Seleccionar el nuevo si es posible (no tenemos el ID facil aqui sin refactorizar ClienteDialog)

    def crear_nuevo_producto(self):
        dlg = ProductoDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cmb_producto.clear()
            self.lista_completa_productos = self.session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
            for p in self.lista_completa_productos:
                self.cmb_producto.addItem(f"{p.codigo} - {p.nombre}", p.id)

class DetalleVentaDialog(QDialog):
    """Diálogo de solo lectura para mostrar el detalle de una venta."""
    def __init__(self, venta, detalles, session, parent=None):
        super().__init__(parent)
        self.venta = venta
        self.detalles = detalles
        self.session = session
        self.setWindowTitle(f"Detalle: {venta.tipo_documento.value} {venta.numero_documento}")
        self.setMinimumSize(800, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Datos
        form = QFormLayout()
        form.addRow("Cliente:", QLabel(self.venta.cliente.razon_social_o_nombre))
        form.addRow("Fecha:", QLabel(self.venta.fecha.strftime('%d/%m/%Y')))
        form.addRow("Documento:", QLabel(f"{self.venta.tipo_documento.value} {self.venta.numero_documento}"))
        
        moneda_txt = "SOLES" if self.venta.moneda == Moneda.SOLES else "DOLARES"
        form.addRow("Moneda:", QLabel(f"{moneda_txt} (TC: {self.venta.tipo_cambio})"))
        layout.addLayout(form)

        # Tabla
        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(["Producto", "Almacén", "Cantidad", "P. Unit", "Subtotal"])
        tabla.setRowCount(len(self.detalles))

        simbolo = "S/" if self.venta.moneda == Moneda.SOLES else "$"

        for i, det in enumerate(self.detalles):
            prod = self.session.query(Producto).get(det.producto_id)
            alm = self.session.query(Almacen).get(det.almacen_id)

            tabla.setItem(i, 0, QTableWidgetItem(prod.nombre if prod else "N/A"))
            tabla.setItem(i, 1, QTableWidgetItem(alm.nombre if alm else "N/A"))
            tabla.setItem(i, 2, QTableWidgetItem(f"{det.cantidad:,.2f}"))
            tabla.setItem(i, 3, QTableWidgetItem(f"{simbolo} {det.precio_unitario:,.2f}"))
            tabla.setItem(i, 4, QTableWidgetItem(f"{simbolo} {det.subtotal:,.2f}"))

        tabla.resizeColumnsToContents()
        layout.addWidget(tabla)

        # Totales
        lbl_tot = QLabel(f"TOTAL: {simbolo} {self.venta.total:,.2f}")
        lbl_tot.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 10px;")
        layout.addWidget(lbl_tot, alignment=Qt.AlignmentFlag.AlignRight)

        btn = QPushButton("Cerrar")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class VentasWindow(QWidget):
    """Ventana principal de ventas"""
    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.ventas_manager = VentasManager(self.session)
        self.init_ui()
        self.cargar_ventas()

    def init_ui(self):
        self.setWindowTitle("Gestión de Ventas")
        layout = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        lbl_tit = QLabel("📦 Gestión de Ventas")
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a73e8;")

        btn_nueva = QPushButton("Nueva Venta (F2)")
        style_button(btn_nueva, 'add', "Nueva Venta")
        btn_nueva.clicked.connect(self.nueva_venta)

        header.addWidget(lbl_tit)
        header.addStretch()
        header.addWidget(btn_nueva)
        layout.addLayout(header)

        # Filtros
        filtros = QHBoxLayout()

        self.cmb_mes = QComboBox()
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        for i, m in enumerate(meses):
            self.cmb_mes.addItem(m, i+1)
        self.cmb_mes.setCurrentIndex(date.today().month - 1)
        self.cmb_mes.currentIndexChanged.connect(self.cargar_ventas)

        self.cmb_cliente_filtro = SearchableComboBox()
        self.cmb_cliente_filtro.addItem("Todos los Clientes", None)
        # Cargar clientes
        clientes = self.session.query(Cliente).filter_by(activo=True).order_by(Cliente.razon_social_o_nombre).all()
        for c in clientes:
            self.cmb_cliente_filtro.addItem(c.razon_social_o_nombre, c.id)
        self.cmb_cliente_filtro.currentIndexChanged.connect(self.cargar_ventas)
        
        btn_refresh = QPushButton("Actualizar")
        btn_refresh.clicked.connect(self.cargar_ventas)
        
        filtros.addWidget(QLabel("Mes:"))
        filtros.addWidget(self.cmb_mes)
        filtros.addWidget(QLabel("Cliente:"))
        filtros.addWidget(self.cmb_cliente_filtro)
        filtros.addWidget(btn_refresh)
        filtros.addStretch()
        layout.addLayout(filtros)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Documento", "Cliente", "Moneda", "Total", "Estado", "Observaciones", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.tabla)
        
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)

    def cargar_ventas(self):
        anio = app_context.get_selected_year()
        mes = self.cmb_mes.currentData()
        cliente_id = self.cmb_cliente_filtro.currentData()
        
        # Filtrar
        query = self.session.query(Venta).filter(
            extract('year', Venta.fecha_registro_contable) == anio,
            extract('month', Venta.fecha_registro_contable) == mes
        )
        
        if cliente_id:
            query = query.filter(Venta.cliente_id == cliente_id)

        ventas = query.order_by(Venta.fecha.desc()).all()

        self.tabla.setRowCount(0)
        total_soles = 0.0

        for i, v in enumerate(ventas):
            self.tabla.insertRow(i)
            self.tabla.setItem(i, 0, QTableWidgetItem(v.fecha.strftime('%d/%m/%Y')))
            self.tabla.setItem(i, 1, QTableWidgetItem(f"{v.tipo_documento.value} {v.numero_documento}"))
            self.tabla.setItem(i, 2, QTableWidgetItem(v.cliente.razon_social_o_nombre))

            simbolo = "S/" if v.moneda == Moneda.SOLES else "$"
            self.tabla.setItem(i, 3, QTableWidgetItem(v.moneda.value))
            self.tabla.setItem(i, 4, QTableWidgetItem(f"{simbolo} {v.total:,.2f}"))

            estado = "Registrado" # Podría ser Anulado si tuvieramos ese flag
            self.tabla.setItem(i, 5, QTableWidgetItem(estado))
            self.tabla.setItem(i, 6, QTableWidgetItem(v.observaciones or ""))

            # Botones
            widget_btns = QWidget()
            layout_btns = QHBoxLayout()
            layout_btns.setContentsMargins(0,0,0,0)

            btn_ver = QPushButton("👁️")
            btn_ver.setToolTip("Ver Detalle")
            btn_ver.clicked.connect(lambda _, x=v: self.ver_venta(x))

            btn_edit = QPushButton("✏️")
            btn_edit.setToolTip("Editar")
            btn_edit.clicked.connect(lambda _, x=v: self.editar_venta(x))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("Eliminar")
            btn_del.setStyleSheet("color: red;")
            btn_del.clicked.connect(lambda _, x=v: self.eliminar_venta(x))

            layout_btns.addWidget(btn_ver)
            layout_btns.addWidget(btn_edit)
            layout_btns.addWidget(btn_del)
            widget_btns.setLayout(layout_btns)

            self.tabla.setCellWidget(i, 7, widget_btns)

            # Sumar al total (convertido a soles aprox para referencia)
            if v.moneda == Moneda.SOLES:
                total_soles += v.total
            else:
                total_soles += v.total * v.tipo_cambio

        self.lbl_status.setText(f"Mostrando {len(ventas)} ventas. Total Aprox (S/): {total_soles:,.2f}")

    def nueva_venta(self):
        dlg = VentaDialog(self, self.user_info)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_ventas()

    def ver_venta(self, venta):
        detalles = self.session.query(VentaDetalle).filter_by(venta_id=venta.id).all()
        dlg = DetalleVentaDialog(venta, detalles, self.session, self)
        dlg.exec()

    def editar_venta(self, venta):
        # Verificar año cerrado
        try:
            verificar_estado_anio(venta.fecha_registro_contable)
        except AnioCerradoError as e:
            QMessageBox.warning(self, "No permitido", str(e))
            return

        detalles = self.session.query(VentaDetalle).filter_by(venta_id=venta.id).all()
        dlg = VentaDialog(self, self.user_info, venta, detalles)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_ventas()

    def eliminar_venta(self, venta):
        # Verificar año cerrado
        try:
            verificar_estado_anio(venta.fecha_registro_contable)
        except AnioCerradoError as e:
            QMessageBox.warning(self, "No permitido", str(e))
            return
            
        res = QMessageBox.question(self, "Confirmar",
                                   f"¿Eliminar venta {venta.numero_documento}?\nEsto revertirá el stock.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            try:
                self.ventas_manager.eliminar_venta(venta.id)
                QMessageBox.information(self, "Éxito", "Venta eliminada")
                self.cargar_ventas()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", str(e))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2:
            self.nueva_venta()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    win = VentasWindow()
    win.show()
    sys.exit(app.exec())
