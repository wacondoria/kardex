"""
Gestión de Compras - Sistema Kardex Valorizado
Archivo: src/views/compras_window.py
(Versión corregida y unificada)
"""

import sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

# Agregar src al path si es necesario (para resolver importaciones locales)
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox,
                             QTextEdit, QCheckBox, QMessageBox, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QSpinBox,
                             QSizePolicy, QFileDialog, QCompleter, QApplication)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QFont, QKeyEvent, QStandardItemModel, QStandardItem

import calendar
import shutil

from sqlalchemy import func, extract
from sqlalchemy.orm import joinedload

from models.database_model import obtener_session
from models.database_model import Compra, CompraDetalle, Proveedor, Producto, Almacen, Moneda, TipoDocumento
from utils.kardex_manager import KardexManager, AnioCerradoError
from utils.compras_manager import ComprasManager
from utils.button_utils import style_button
from utils.widgets import MoneyDelegate, SearchableComboBox
from utils.app_context import app_context
from utils.styles import STYLE_CUADRADO_VERDE

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    pass

# Import dialogs
try:
    from views.proveedores_window import ProveedorDialog
except ImportError:
    ProveedorDialog = None

try:
    from views.productos_window import ProductoDialog
except ImportError:
    ProductoDialog = None

class CompraDialog(QDialog):
    """Diálogo para crear o editar una compra."""

    def __init__(self, parent=None, user_info=None, compra_a_editar=None, detalles_originales=None):
        super().__init__(parent)
        self.user_info = user_info
        self.compra_a_editar = compra_a_editar
        self.detalles_originales = detalles_originales or []
        self.session = obtener_session()
        self.detalles_compra = [] # Lista de dicts para la tabla
        self.compras_manager = ComprasManager(self.session)

        self.setWindowTitle("Nueva Compra" if not self.compra_a_editar else f"Editar Compra {self.compra_a_editar.numero_documento}")
        self.setMinimumSize(900, 650)

        self.init_ui()

        if self.compra_a_editar:
            self.cargar_datos()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Datos Generales ---
        grupo_datos = QGroupBox("Datos del Documento")
        layout_datos = QFormLayout()
        
        # Proveedor
        self.cmb_ruc_proveedor = SearchableComboBox()
        self.cmb_ruc_proveedor.setPlaceholderText("RUC")
        self.cmb_ruc_proveedor.currentIndexChanged.connect(self.sincronizar_por_ruc)

        self.cmb_nombre_proveedor = SearchableComboBox()
        self.cmb_nombre_proveedor.setPlaceholderText("Razón Social")
        self.cmb_nombre_proveedor.currentIndexChanged.connect(self.sincronizar_por_nombre)

        self.btn_nuevo_proveedor = QPushButton("+")
        self.btn_nuevo_proveedor.setFixedSize(30, 30)
        self.btn_nuevo_proveedor.setStyleSheet(STYLE_CUADRADO_VERDE)
        self.btn_nuevo_proveedor.clicked.connect(self.crear_nuevo_proveedor)
        
        h_prov = QHBoxLayout()
        h_prov.addWidget(self.cmb_ruc_proveedor, 1)
        h_prov.addWidget(self.cmb_nombre_proveedor, 3)
        h_prov.addWidget(self.btn_nuevo_proveedor)
        layout_datos.addRow("Proveedor:", h_prov)
        
        # Cargar proveedores
        provs = self.session.query(Proveedor).filter_by(activo=True).order_by(Proveedor.razon_social).all()
        for p in provs:
            self.cmb_ruc_proveedor.addItem(p.ruc, p.id)
            self.cmb_nombre_proveedor.addItem(p.razon_social, p.id)
            
        # Fechas
        self.date_fecha = QDateEdit(QDate.currentDate())
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.dateChanged.connect(self.sincronizar_fecha_contable)
        
        self.date_fecha_contable = QDateEdit(QDate.currentDate())
        self.date_fecha_contable.setCalendarPopup(True)
        
        h_fechas = QHBoxLayout()
        h_fechas.addWidget(QLabel("Fecha Emisión:"))
        h_fechas.addWidget(self.date_fecha)
        h_fechas.addWidget(QLabel("Fecha Contable:"))
        h_fechas.addWidget(self.date_fecha_contable)
        layout_datos.addRow(h_fechas)
        
        # Documento
        self.cmb_tipo_doc = QComboBox()
        self.cmb_tipo_doc.addItems(["FACTURA", "BOLETA", "GUIA", "NOTA_CREDITO", "NOTA_DEBITO"])
        
        self.txt_numero_doc = QLineEdit()
        self.txt_numero_doc.editingFinished.connect(self.formatear_numero_documento)
        
        h_doc = QHBoxLayout()
        h_doc.addWidget(self.cmb_tipo_doc)
        h_doc.addWidget(QLabel("Nro:"))
        h_doc.addWidget(self.txt_numero_doc)
        layout_datos.addRow("Documento:", h_doc)
        
        # Moneda y TC
        self.cmb_moneda = QComboBox()
        self.cmb_moneda.addItem("SOLES (S/)", Moneda.SOLES)
        self.cmb_moneda.addItem("DOLARES ($)", Moneda.DOLARES)
        
        self.spn_tc = QDoubleSpinBox()
        self.spn_tc.setDecimals(3)
        self.spn_tc.setRange(0.001, 100.0)
        self.spn_tc.setValue(1.000)
        
        h_moneda = QHBoxLayout()
        h_moneda.addWidget(self.cmb_moneda)
        h_moneda.addWidget(QLabel("T. Cambio:"))
        h_moneda.addWidget(self.spn_tc)
        layout_datos.addRow("Moneda:", h_moneda)
        
        # Checkbox IGV
        self.chk_incluye_igv = QCheckBox("Los precios unitarios incluyen IGV")
        self.chk_incluye_igv.setChecked(True)
        layout_datos.addRow("", self.chk_incluye_igv)
        
        grupo_datos.setLayout(layout_datos)
        layout.addWidget(grupo_datos)
        
        # --- Agregar Productos ---
        grupo_agregar = QGroupBox("Agregar Producto")
        layout_agregar = QHBoxLayout()
        
        self.cmb_producto = SearchableComboBox()
        self.btn_nuevo_producto = QPushButton("+")
        self.btn_nuevo_producto.setFixedSize(30, 30)
        self.btn_nuevo_producto.setStyleSheet(STYLE_CUADRADO_VERDE)
        self.btn_nuevo_producto.clicked.connect(self.crear_nuevo_producto)
        
        # Cargar productos
        self.lista_completa_productos = self.session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
        for p in self.lista_completa_productos:
            self.cmb_producto.addItem(f"{p.codigo} - {p.nombre}", p.id)
            
        self.cmb_almacen = QComboBox()
        almacenes = self.session.query(Almacen).filter_by(activo=True).all()
        for a in almacenes:
            self.cmb_almacen.addItem(a.nombre, a.id)
            
        self.spn_cantidad = QDoubleSpinBox()
        self.spn_cantidad.setRange(0.01, 999999)
        self.spn_cantidad.setPrefix("Cant: ")
        
        self.spn_precio = QDoubleSpinBox()
        self.spn_precio.setRange(0.00, 99999999)
        self.spn_precio.setPrefix("P.U: ")
        
        self.btn_agregar = QPushButton("Agregar")
        self.btn_agregar.clicked.connect(self.agregar_detalle)
        
        layout_agregar.addWidget(QLabel("Prod:"))
        layout_agregar.addWidget(self.cmb_producto, 2)
        layout_agregar.addWidget(self.btn_nuevo_producto)
        layout_agregar.addWidget(QLabel("Alm:"))
        layout_agregar.addWidget(self.cmb_almacen, 1)
        layout_agregar.addWidget(self.spn_cantidad)
        layout_agregar.addWidget(self.spn_precio)
        layout_agregar.addWidget(self.btn_agregar)
        
        grupo_agregar.setLayout(layout_agregar)
        layout.addWidget(grupo_agregar)
        
        # --- Tabla Detalles ---
        self.tabla_productos = QTableWidget()
        self.tabla_productos.setColumnCount(6)
        self.tabla_productos.setHorizontalHeaderLabels(["Producto", "Almacén", "Cantidad", "P. Unit", "Subtotal", "Accion"])
        self.tabla_productos.cellChanged.connect(self.detalle_editado)
        layout.addWidget(self.tabla_productos)
        
        # --- Totales ---
        layout_totales = QFormLayout()
        self.lbl_subtotal = QLabel("0.00")
        self.lbl_igv = QLabel("0.00")
        self.lbl_total = QLabel("0.00")
        
        layout_totales.addRow("Subtotal:", self.lbl_subtotal)
        layout_totales.addRow("IGV:", self.lbl_igv)
        layout_totales.addRow("Total:", self.lbl_total)
        
        h_bottom = QHBoxLayout()
        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setPlaceholderText("Observaciones...")
        self.txt_observaciones.setMaximumHeight(60)
        
        h_bottom.addWidget(self.txt_observaciones, 2)
        h_bottom.addLayout(layout_totales, 1)
        layout.addLayout(h_bottom)
        
        # --- Botones Finales ---
        h_btns = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar Compra (F4)")
        self.btn_guardar.clicked.connect(self.guardar_compra)
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        
        h_btns.addStretch()
        h_btns.addWidget(self.btn_guardar)
        h_btns.addWidget(self.btn_cancelar)
        layout.addLayout(h_btns)
        
        # Install event filters for navigation
        self.cmb_producto.installEventFilter(self)
        self.cmb_almacen.installEventFilter(self)
        self.spn_cantidad.installEventFilter(self)
        self.spn_precio.installEventFilter(self)
        self.btn_agregar.installEventFilter(self)

    def cargar_datos(self):
        """Carga los datos de la compra a editar."""
        if not self.compra_a_editar:
            self.cmb_ruc_proveedor.setCurrentIndex(-1)
            self.cmb_nombre_proveedor.setCurrentIndex(-1)
            return
            
        c = self.compra_a_editar
        
        # Set fields
        index = self.cmb_ruc_proveedor.findData(c.proveedor_id)
        if index >= 0:
            self.cmb_ruc_proveedor.setCurrentIndex(index)
            # El nombre se sincroniza automáticamente, pero por seguridad:
            self.cmb_nombre_proveedor.setCurrentIndex(self.cmb_nombre_proveedor.findData(c.proveedor_id))
        
        self.date_fecha.setDate(c.fecha)
        if c.fecha_registro_contable:
            self.date_fecha_contable.setDate(c.fecha_registro_contable)
            
        self.cmb_tipo_doc.setCurrentText(c.tipo_documento.name)
        self.txt_numero_doc.setText(c.numero_documento)
        
        idx_moneda = self.cmb_moneda.findData(c.moneda)
        if idx_moneda >= 0: self.cmb_moneda.setCurrentIndex(idx_moneda)
        
        self.spn_tc.setValue(float(c.tipo_cambio))
        self.chk_incluye_igv.setChecked(c.incluye_igv)
        self.txt_observaciones.setText(c.observaciones or "")
        
        # Load details
        signal_states = {
            self.tabla_productos: self.tabla_productos.signalsBlocked()
        }
        
        try:
            self.tabla_productos.blockSignals(True)
            
            for det_obj in self.detalles_originales:
                producto = self.session.get(Producto, det_obj.producto_id)
                almacen = self.session.get(Almacen, det_obj.almacen_id)
                
                cantidad_orig = det_obj.cantidad

                # Recuperar precio unitario para la UI (desde precio_unitario_sin_igv)
                precio_base = Decimal(str(det_obj.precio_unitario_sin_igv))
                if c.incluye_igv:
                    igv_pct = Decimal(str(c.igv_porcentaje)) if getattr(c, 'igv_porcentaje', None) else Decimal('18.0')
                    factor = Decimal('1') + (igv_pct / Decimal('100'))
                    precio_ui = precio_base * factor
                else:
                    precio_ui = precio_base

                subtotal_ui = det_obj.subtotal
                
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

    def agregar_detalle(self):
        prod_id = self.cmb_producto.currentData()
        alm_id = self.cmb_almacen.currentData()
        cant = self.spn_cantidad.value()
        precio = self.spn_precio.value()
        
        if not prod_id or not alm_id:
            return
            
        prod_txt = self.cmb_producto.currentText()
        alm_txt = self.cmb_almacen.currentText()
        
        # Calcular subtotal preliminar
        sub = cant * precio
        
        det = {
            'producto_id': prod_id,
            'producto_nombre': prod_txt,
            'almacen_id': alm_id,
            'almacen_nombre': alm_txt,
            'cantidad': cant,
            'precio_unitario': precio,
            'subtotal': sub,
            'detalle_original_id': None
        }
        self.detalles_compra.append(det)
        self.actualizar_tabla_productos()
        self.recalcular_totales()
        
        # Reset fields
        self.spn_cantidad.setValue(0)
        self.spn_precio.setValue(0)
        self.cmb_producto.setFocus()

    def actualizar_tabla_productos(self):
        self.tabla_productos.setRowCount(0)
        self.tabla_productos.setRowCount(len(self.detalles_compra))
        
        for i, det in enumerate(self.detalles_compra):
            # Producto (ComboBox para editar)
            cb_prod = QComboBox()
            cb_prod.addItem(det['producto_nombre'], det['producto_id'])
            self.tabla_productos.setCellWidget(i, 0, cb_prod)
            
            self.tabla_productos.setItem(i, 1, QTableWidgetItem(det['almacen_nombre']))
            self.tabla_productos.setItem(i, 2, QTableWidgetItem(f"{det['cantidad']:,.2f}"))
            self.tabla_productos.setItem(i, 3, QTableWidgetItem(f"{det['precio_unitario']:,.2f}"))
            self.tabla_productos.setItem(i, 4, QTableWidgetItem(f"{det['subtotal']:,.2f}"))
            
            btn_del = QPushButton("X")
            btn_del.clicked.connect(lambda ch, idx=i: self.eliminar_detalle(idx))
            self.tabla_productos.setCellWidget(i, 5, btn_del)

    def eliminar_detalle(self, index):
        if 0 <= index < len(self.detalles_compra):
            del self.detalles_compra[index]
            self.actualizar_tabla_productos()
            self.recalcular_totales()

    def recalcular_totales(self):
        subtotal = Decimal(0)
        igv = Decimal(0)
        total = Decimal(0)
        
        incluye_igv = self.chk_incluye_igv.isChecked()
        
        for det in self.detalles_compra:
            cant = Decimal(str(det['cantidad']))
            precio = Decimal(str(det['precio_unitario']))
            
            if incluye_igv:
                # Precio incluye IGV
                sub_linea = cant * precio
                base_linea = sub_linea / Decimal('1.18')
                igv_linea = sub_linea - base_linea
            else:
                # Precio mas IGV
                base_linea = cant * precio
                igv_linea = base_linea * Decimal('0.18')
                sub_linea = base_linea + igv_linea
                
            subtotal += base_linea
            igv += igv_linea
            total += sub_linea
            
            # Actualizar subtotal en dict visual (aproximado)
            det['subtotal'] = float(sub_linea)

        self.lbl_subtotal.setText(f"{subtotal:,.2f}")
        self.lbl_igv.setText(f"{igv:,.2f}")
        self.lbl_total.setText(f"{total:,.2f}")

    def guardar_compra(self):
        if not self.detalles_compra:
            QMessageBox.warning(self, "Error", "Debe agregar al menos un producto.")
            return

        proveedor_id = self.cmb_ruc_proveedor.currentData()
        if not proveedor_id:
            QMessageBox.warning(self, "Error", "Debe seleccionar un proveedor.")
            return
            
        try:
            # 1. Preparar datos de cabecera
            datos_cabecera = {
                'proveedor_id': proveedor_id,
                'fecha': self.date_fecha.date().toPyDate(),
                'fecha_registro_contable': self.date_fecha_contable.date().toPyDate(),
                'tipo_documento': self.cmb_tipo_doc.currentText(),
                'numero_documento': self.txt_numero_doc.text(),
                'moneda': self.cmb_moneda.currentData(),
                'tipo_cambio': Decimal(str(self.spn_tc.value())),
                'incluye_igv': self.chk_incluye_igv.isChecked(),
                'observaciones': self.txt_observaciones.toPlainText(),
            }
            
            # 3. Llamar al manager
            compra_id = self.compra_a_editar.id if self.compra_a_editar else None
            
            self.compras_manager.guardar_compra(datos_cabecera, self.detalles_compra, compra_id=compra_id)
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}")

    def detalle_editado(self, row, column):
        if column not in [2, 3]:
            return
        item = self.tabla_productos.item(row, column)
        if not item:
            return
        # Eliminar comas (separador de miles) antes de convertir
        nuevo_valor_str = item.text().replace(',', '')

        try:
            nuevo_valor = float(nuevo_valor_str)
            if nuevo_valor < 0:
                 raise ValueError("Valor no puede ser negativo")
        except ValueError:
            QMessageBox.warning(self, "Valor inválido", f"Ingrese un número válido.")
            self.tabla_productos.blockSignals(True)
            if column == 2:
                 item.setText(f"{self.detalles_compra[row]['cantidad']:,.2f}")
            else:
                 item.setText(f"{self.detalles_compra[row]['precio_unitario']:,.2f}")
            self.tabla_productos.blockSignals(False)
            return

        detalle_actualizado = self.detalles_compra[row]
        if column == 2:
            detalle_actualizado['cantidad'] = nuevo_valor
        else:
            detalle_actualizado['precio_unitario'] = nuevo_valor

        cantidad_actual = Decimal(str(detalle_actualizado['cantidad']))
        precio_actual = Decimal(str(detalle_actualizado['precio_unitario']))

        IGV_FACTOR = Decimal('1.18')
        DOS_DECIMALES = Decimal('0.01')
        subtotal_sin_igv = Decimal('0')

        if self.chk_incluye_igv.isChecked():
            subtotal_sin_igv = (cantidad_actual * (precio_actual / IGV_FACTOR)).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
        else:
            subtotal_sin_igv = (cantidad_actual * precio_actual).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

        detalle_actualizado['subtotal'] = float(subtotal_sin_igv)

        self.tabla_productos.blockSignals(True)
        subtotal_item = self.tabla_productos.item(row, 4)
        if not subtotal_item:
             subtotal_item = QTableWidgetItem()
             subtotal_item.setFlags(subtotal_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
             self.tabla_productos.setItem(row, 4, subtotal_item)
        subtotal_item.setText(f"{detalle_actualizado['subtotal']:,.2f}")
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
                    if self.cmb_producto.completer.popup().isVisible():
                        return super().eventFilter(source, event)
                    self.cmb_almacen.setFocus()
                    return True

                elif source is self.cmb_almacen:
                    if hasattr(self.cmb_almacen, 'completer') and self.cmb_almacen.completer and self.cmb_almacen.completer.popup().isVisible():
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
        if ProveedorDialog is None:
            QMessageBox.critical(self, "Error",
                "El módulo de proveedores ('proveedores_window.py') no se pudo cargar.")
            return

        dialog = ProveedorDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cmb_ruc_proveedor.clear()
            self.cmb_nombre_proveedor.clear()

            proveedores = self.session.query(Proveedor).filter_by(activo=True).order_by(Proveedor.razon_social).all()
            for prov in proveedores:
                self.cmb_ruc_proveedor.addItem(prov.ruc, prov.id)
                self.cmb_nombre_proveedor.addItem(prov.razon_social, prov.id)

            if hasattr(dialog, 'nuevo_proveedor_id') and dialog.nuevo_proveedor_id:
               index = self.cmb_ruc_proveedor.findData(dialog.nuevo_proveedor_id)
               if index != -1: self.cmb_ruc_proveedor.setCurrentIndex(index)

    def sincronizar_por_ruc(self, index):
        """Sincroniza el combo de nombre al cambiar el RUC."""
        if index == -1: return
        prov_id = self.cmb_ruc_proveedor.currentData()

        self.cmb_nombre_proveedor.blockSignals(True)
        idx_nombre = self.cmb_nombre_proveedor.findData(prov_id)
        if idx_nombre != -1:
            self.cmb_nombre_proveedor.setCurrentIndex(idx_nombre)
        self.cmb_nombre_proveedor.blockSignals(False)

    def sincronizar_por_nombre(self, index):
        """Sincroniza el combo de RUC al cambiar el nombre."""
        if index == -1: return
        prov_id = self.cmb_nombre_proveedor.currentData()

        self.cmb_ruc_proveedor.blockSignals(True)
        idx_ruc = self.cmb_ruc_proveedor.findData(prov_id)
        if idx_ruc != -1:
            self.cmb_ruc_proveedor.setCurrentIndex(idx_ruc)
        self.cmb_ruc_proveedor.blockSignals(False)

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
                if index != -1: self.cmb_producto.setCurrentIndex(index)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4:
            self.guardar_compra()
        else:
            super().keyPressEvent(event)


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
            tabla.setItem(row, 2, QTableWidgetItem(f"{det.cantidad:,.2f}"))
            tabla.setItem(row, 3, QTableWidgetItem(f"{det.precio_unitario_sin_igv:,.2f}"))
            tabla.setItem(row, 4, QTableWidgetItem(f"{det.subtotal:,.2f}"))

        tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tabla.resizeColumnsToContents()

        money_delegate = MoneyDelegate(tabla)
        tabla.setItemDelegateForColumn(2, money_delegate)
        tabla.setItemDelegateForColumn(3, money_delegate)
        tabla.setItemDelegateForColumn(4, money_delegate)

        layout.addWidget(tabla)

        # --- Totales ---
        grupo_totales = QGroupBox("Resumen de Totales (Compra)")
        form_totales = QFormLayout()
        simbolo = "$" if self.compra.moneda == Moneda.DOLARES else "S/"

        self.lbl_subtotal_detalle = QLabel(f"{simbolo} --.--")
        form_totales.addRow(QLabel("<b>Subtotal Compra:</b>"), self.lbl_subtotal_detalle)
        self.lbl_igv_detalle = QLabel(f"{simbolo} --.--")
        form_totales.addRow(QLabel("<b>IGV (18%):</b>"), self.lbl_igv_detalle)
        self.lbl_total_detalle = QLabel(f"{simbolo} --.--")
        self.lbl_total_detalle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a73e8;")
        form_totales.addRow(QLabel("<b>TOTAL COMPRA:</b>"), self.lbl_total_detalle)

        grupo_totales.setLayout(form_totales)
        grupo_totales.setMaximumWidth(350)

        totales_layout = QHBoxLayout()
        totales_layout.addStretch()
        totales_layout.addWidget(grupo_totales)
        layout.addLayout(totales_layout)

        # --- Boton Cerrar ---
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

    def recalcular_totales_locales(self):
        """Muestra los totales almacenados en la compra."""
        subtotal_real = Decimal(str(getattr(self.compra, 'subtotal', '0')))
        igv_real = Decimal(str(getattr(self.compra, 'igv', '0')))
        total_real = Decimal(str(getattr(self.compra, 'total', '0')))
        simbolo = "$" if self.compra.moneda == Moneda.DOLARES else "S/"

        self.lbl_subtotal_detalle.setText(f"{simbolo} {subtotal_real:,.2f}")
        self.lbl_igv_detalle.setText(f"{simbolo} {igv_real:,.2f}")
        self.lbl_total_detalle.setText(f"{simbolo} {total_real:,.2f}")


class ComprasWindow(QWidget):
    """Ventana principal de gestión de compras."""

    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.compras_mostradas = []
        self.compras_manager = ComprasManager(self.session)

        self.init_ui()
        self.cargar_compras()

    def init_ui(self):
        self.setWindowTitle("Gestión de Compras")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        titulo = QLabel("🛒 Gestión de Compras")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")

        btn_nueva = QPushButton()
        style_button(btn_nueva, 'add', "Nueva Compra (F2)")
        btn_nueva.clicked.connect(self.nueva_compra)
        if self.user_info and self.user_info.get('licencia_vencida'):
            btn_nueva.setEnabled(False)

        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nueva)
        layout.addLayout(header_layout)

        # Filtros
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
        self.cmb_mes_filtro.currentIndexChanged.connect(self.cargar_compras)

        self.cmb_proveedor_filtro = SearchableComboBox()
        self.cmb_proveedor_filtro.addItem("Todos los proveedores", None)
        self.recargar_filtro_proveedores()
        self.cmb_proveedor_filtro.currentIndexChanged.connect(self.cargar_compras)

        self.cmb_vista_moneda = QComboBox()
        self.cmb_vista_moneda.addItem("Ver en Moneda de Origen", "ORIGEN")
        self.cmb_vista_moneda.addItem("Mostrar Todo en SOLES (S/)", "SOLES")
        self.cmb_vista_moneda.currentIndexChanged.connect(self.cargar_compras)

        filtro_layout.addWidget(self.cmb_mes_filtro)
        filtro_layout.addWidget(self.cmb_proveedor_filtro)
        filtro_layout.addWidget(self.cmb_vista_moneda)
        filtro_layout.addStretch()
        layout.addLayout(filtro_layout)

        self.lbl_contador = QLabel("Cargando...")
        layout.addWidget(self.lbl_contador)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(10)
        self.tabla.setHorizontalHeaderLabels([
            "Nro. Proceso", "F. Contable", "F. Emisión", "Documento", "Proveedor", "Moneda", "Subtotal", "IGV", "Total", "Acciones"
        ])
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setAlternatingRowColors(True)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(9, 250)

        money_delegate = MoneyDelegate(self.tabla)
        self.tabla.setItemDelegateForColumn(6, money_delegate)
        self.tabla.setItemDelegateForColumn(7, money_delegate)
        self.tabla.setItemDelegateForColumn(8, money_delegate)

        layout.addWidget(self.tabla)

    def recargar_filtro_proveedores(self):
        self.cmb_proveedor_filtro.blockSignals(True)
        self.cmb_proveedor_filtro.clear()
        self.cmb_proveedor_filtro.addItem("Todos los proveedores", None)

        proveedores = self.session.query(Proveedor).filter_by(activo=True).order_by(Proveedor.razon_social).all()
        for p in proveedores:
            self.cmb_proveedor_filtro.addItem(p.razon_social, p.id)

        self.cmb_proveedor_filtro.blockSignals(False)

    def cargar_compras(self):
        mes_sel = self.cmb_mes_filtro.currentData()
        anio_sel = app_context.get_selected_year()
        if not mes_sel or not anio_sel: return

        primer_dia, num_dias = calendar.monthrange(anio_sel, mes_sel)
        fecha_desde = date(anio_sel, mes_sel, 1)
        fecha_hasta = date(anio_sel, mes_sel, num_dias)

        prov_id = self.cmb_proveedor_filtro.currentData()

        temp_session = obtener_session()
        compras = []
        try:
            columna_fecha_filtro = func.coalesce(Compra.fecha_registro_contable, Compra.fecha)
            query = temp_session.query(Compra).options(joinedload(Compra.proveedor))

            query = query.filter(
                columna_fecha_filtro >= fecha_desde,
                columna_fecha_filtro <= fecha_hasta
            )

            if prov_id:
                query = query.filter_by(proveedor_id=prov_id)

            compras = query.order_by(columna_fecha_filtro.asc(), Compra.id.asc()).all()

        except Exception as e:
             QMessageBox.critical(self, "Error al Cargar Compras", f"No se pudieron cargar los datos:\n{e}")
        finally:
             temp_session.close()

        self.mostrar_compras(compras)

    def mostrar_compras(self, compras):
        self.compras_mostradas = compras
        self.tabla.setRowCount(len(compras))

        total_soles = Decimal('0')
        vista_moneda = self.cmb_vista_moneda.currentData()

        for row, compra in enumerate(compras):
            sub = Decimal(str(compra.subtotal or 0))
            igv = Decimal(str(compra.igv or 0))
            tot = Decimal(str(compra.total or 0))
            tc = Decimal(str(compra.tipo_cambio or 1))

            simbolo = "S/"
            if vista_moneda == 'SOLES':
                if compra.moneda == Moneda.DOLARES:
                    sub = sub * tc
                    igv = igv * tc
                    tot = tot * tc
            else:
                simbolo = "$" if compra.moneda == Moneda.DOLARES else "S/"

            if compra.moneda == Moneda.DOLARES:
                total_soles += (Decimal(str(compra.total or 0)) * tc)
            else:
                total_soles += Decimal(str(compra.total or 0))

            self.tabla.setItem(row, 0, QTableWidgetItem(compra.numero_proceso or ""))

            f_cont = compra.fecha_registro_contable
            self.tabla.setItem(row, 1, QTableWidgetItem(f_cont.strftime('%d/%m/%Y') if f_cont else ""))
            self.tabla.setItem(row, 2, QTableWidgetItem(compra.fecha.strftime('%d/%m/%Y')))
            self.tabla.setItem(row, 3, QTableWidgetItem(f"{compra.tipo_documento.value} {compra.numero_documento}"))

            prov_nom = compra.proveedor.razon_social if compra.proveedor else "Desconocido"
            self.tabla.setItem(row, 4, QTableWidgetItem(prov_nom))

            self.tabla.setItem(row, 5, QTableWidgetItem(simbolo))
            self.tabla.setItem(row, 6, QTableWidgetItem(f"{simbolo} {sub:,.2f}"))
            self.tabla.setItem(row, 7, QTableWidgetItem(f"{simbolo} {igv:,.2f}"))
            self.tabla.setItem(row, 8, QTableWidgetItem(f"{simbolo} {tot:,.2f}"))

            # Botones
            widget_btns = QWidget()
            layout_btns = QHBoxLayout(widget_btns)
            layout_btns.setContentsMargins(0, 0, 0, 0)
            layout_btns.setSpacing(5)

            btn_ver = QPushButton()
            style_button(btn_ver, 'view', "Ver")
            btn_ver.clicked.connect(lambda ch, c=compra: self.ver_detalle(c))
            layout_btns.addWidget(btn_ver)

            btn_edit = QPushButton()
            style_button(btn_edit, 'edit', "Editar")
            btn_edit.clicked.connect(lambda ch, c=compra: self.editar_compra(c))
            if self.user_info and self.user_info.get('licencia_vencida'):
                 btn_edit.setEnabled(False)
            layout_btns.addWidget(btn_edit)

            btn_del = QPushButton()
            style_button(btn_del, 'delete', "Eliminar")
            btn_del.clicked.connect(lambda ch, c=compra: self.eliminar_compra(c))
            if self.user_info and self.user_info.get('licencia_vencida'):
                 btn_del.setEnabled(False)
            layout_btns.addWidget(btn_del)

            layout_btns.addStretch()
            self.tabla.setCellWidget(row, 9, widget_btns)

        self.lbl_contador.setText(f"Total: {len(compras)} compras | Total Soles: S/ {total_soles:,.2f}")

    def nueva_compra(self):
        dialog = CompraDialog(self, self.user_info)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_compras()

    def ver_detalle(self, compra_stale):
        try:
            self.session.expire_all()
            compra = self.session.get(Compra, compra_stale.id)
            if not compra: return

            detalles = self.session.query(CompraDetalle).filter_by(compra_id=compra.id).all()
            dialog = DetalleCompraDialog(compra, detalles, self.session, self)
            dialog.exec()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al cargar detalle: {e}")

    def editar_compra(self, compra):
        try:
            detalles = self.session.query(CompraDetalle).filter_by(compra_id=compra.id).all()
            dialog = CompraDialog(self, self.user_info, compra, detalles)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.cargar_compras()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al editar: {e}")

    def eliminar_compra(self, compra):
        confirmar = QMessageBox.warning(self, "Confirmar",
            "¿Eliminar compra? Esto revertirá el stock.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirmar == QMessageBox.StandardButton.Yes:
            try:
                self.compras_manager.eliminar_compra(compra.id)
                QMessageBox.information(self, "Éxito", "Compra eliminada.")
                self.cargar_compras()
            except AnioCerradoError as e:
                QMessageBox.warning(self, "Error", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2:
            self.nueva_compra()
        elif event.key() == Qt.Key.Key_F6:
            row = self.tabla.currentRow()
            if row >= 0 and row < len(self.compras_mostradas):
                self.editar_compra(self.compras_mostradas[row])
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app_context.set_selected_year(datetime.now().year)
    # Mock user info for standalone run
    user_info = {'username': 'admin', 'rol': 'ADMIN', 'licencia_vencida': False}

    app = QApplication(sys.argv)
    w = ComprasWindow(user_info)
    w.show()
    sys.exit(app.exec())
