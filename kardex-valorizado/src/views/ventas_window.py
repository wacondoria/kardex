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
from utils.ventas_manager import VentasManager
from utils.app_context import app_context
from utils.widgets import SearchableComboBox

# --- IMPORTACIÓN DE DIÁLOGOS MAESTROS ---
from .productos_window import ProductoDialog
try:
    from .clientes_window import ClienteDialog
except ImportError:
    ClienteDialog = None

class VentasWindow(QWidget):
    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info
        self.session = obtener_session()
        self.ventas_manager = VentasManager(self.session)
        self.detalles_venta = []
        self.lista_completa_productos = []
        self.venta_original = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Gestión de Ventas")
        layout = QVBoxLayout(self)
        
        # Widgets definitions
        self.cmb_doc_cliente = SearchableComboBox()
        self.cmb_nombre_cliente = SearchableComboBox()
        self.txt_numero_proceso = QLineEdit()
        self.txt_serie_doc = QLineEdit()
        self.txt_numero_doc = QLineEdit()
        self.date_fecha = QDateEdit(QDate.currentDate())
        self.date_fecha_contable = QDateEdit(QDate.currentDate())
        self.cmb_tipo_doc = QComboBox()
        self.chk_incluye_igv = QCheckBox("Incluye IGV")
        self.cmb_moneda = QComboBox()
        self.spn_tipo_cambio = QDoubleSpinBox()
        self.cmb_producto = SearchableComboBox()
        self.cmb_almacen = QComboBox()
        self.spn_cantidad = QDoubleSpinBox()
        self.spn_precio = QDoubleSpinBox()
        self.btn_agregar = QPushButton("Agregar")
        self.btn_guardar = QPushButton("Guardar Venta")
        self.tabla_productos = QTableWidget()
        self.lbl_subtotal = QLabel("0.00")
        self.lbl_igv = QLabel("0.00")
        self.lbl_total = QLabel("0.00")
        self.txt_observaciones = QTextEdit()
        
        # Add to layout (simplified)
        layout.addWidget(QLabel("Cliente:"))
        layout.addWidget(self.cmb_doc_cliente)
        layout.addWidget(self.cmb_nombre_cliente)
        layout.addWidget(QLabel("Tipo Doc:"))
        layout.addWidget(self.cmb_tipo_doc)
        layout.addWidget(self.tabla_productos)
        layout.addWidget(self.btn_agregar)
        layout.addWidget(self.btn_guardar)

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

        # --- VERIFICACIÓN DE STOCK (NUEVO) ---
        try:
            # Usar VentasManager para verificar stock
            stock_actual = self.ventas_manager.obtener_stock_actual(prod_id, alm_id)
            stock_en_tabla = sum(
                det['cantidad'] for det in self.detalles_venta 
                if det['producto_id'] == prod_id and det['almacen_id'] == alm_id
            )
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
            cliente_id = self.cmb_doc_cliente.currentData()
            if not cliente_id:
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
                'cliente_id': cliente_id,
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
            self.cmb_doc_cliente, self.cmb_nombre_cliente, self.date_fecha, self.date_fecha_contable,
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

            # Cargar datos cliente
            index_doc = self.cmb_doc_cliente.findData(self.venta_original.cliente_id)
            if index_doc != -1: self.cmb_doc_cliente.setCurrentIndex(index_doc)

            # Sincronizar nombre manualmente ya que las señales están bloqueadas
            index_nom = self.cmb_nombre_cliente.findData(self.venta_original.cliente_id)
            if index_nom != -1: self.cmb_nombre_cliente.setCurrentIndex(index_nom)
            
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
            cliente_id = self.cmb_doc_cliente.currentData()
            if not cliente_id:
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
                'cliente_id': cliente_id,
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
            self.cmb_doc_cliente, self.cmb_nombre_cliente, self.date_fecha, self.date_fecha_contable,
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

            # Cargar datos cliente
            index_doc = self.cmb_doc_cliente.findData(self.venta_original.cliente_id)
            if index_doc != -1: self.cmb_doc_cliente.setCurrentIndex(index_doc)

            # Sincronizar nombre manualmente ya que las señales están bloqueadas
            index_nom = self.cmb_nombre_cliente.findData(self.venta_original.cliente_id)
            if index_nom != -1: self.cmb_nombre_cliente.setCurrentIndex(index_nom)
            
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
            self.cmb_doc_cliente.clear()
            self.cmb_nombre_cliente.clear()

            clientes = self.session.query(Cliente).filter_by(activo=True).order_by(Cliente.razon_social_o_nombre).all()
            for cli in clientes:
                self.cmb_doc_cliente.addItem(cli.ruc_o_dni, cli.id)
                self.cmb_nombre_cliente.addItem(cli.razon_social_o_nombre, cli.id)
            
            if hasattr(dialog, 'nuevo_cliente_id') and dialog.nuevo_cliente_id:
                index = self.cmb_doc_cliente.findData(dialog.nuevo_cliente_id)
                if index != -1: self.cmb_doc_cliente.setCurrentIndex(index)

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
        self.tabla.setColumnWidth(2, 90); self.tabla.setColumnWidth(9, 250)
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

    def eliminar_rango_ventas(self):
        """Elimina un rango de ventas por Número de Proceso (Correlativo)."""
        dialog = DeleteRangeDialog(self, title="Eliminar Rango de Ventas", label_text="Ingrese el rango de Correlativos (Nro. Proceso) a eliminar:")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            desde, hasta = dialog.get_range()
            
            if not desde.isdigit() or not hasta.isdigit():
                QMessageBox.warning(self, "Error", "Los correlativos deben ser numéricos.")
                return
                
            corr_desde = int(desde)
            corr_hasta = int(hasta)
            
            if corr_desde > corr_hasta:
                QMessageBox.warning(self, "Error", "El valor 'Desde' no puede ser mayor que 'Hasta'.")
                return
                
            confirm = QMessageBox.question(self, "Confirmar Eliminación Masiva", 
                                         f"¿Está SEGURO de eliminar las ventas con correlativo del {corr_desde} al {corr_hasta}?\n\n"
                                         "Esta acción anulará los movimientos de Kardex y NO se puede deshacer.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    anio_sel = app_context.get_selected_year()
                    mes_sel = self.cmb_mes_filtro.currentData()
                    if not mes_sel:
                        QMessageBox.warning(self, "Aviso", "Seleccione un mes específico para eliminar por rango de correlativos.")
                        return

                    prefijo = f"05{mes_sel:02d}"
                    
                    primer_dia, num_dias = calendar.monthrange(anio_sel, mes_sel)
                    fecha_desde = date(anio_sel, mes_sel, 1)
                    fecha_hasta = date(anio_sel, mes_sel, num_dias)
                    
                    columna_fecha = func.coalesce(Venta.fecha_registro_contable, Venta.fecha)
                    ventas_mes = self.session.query(Venta).filter(
                        columna_fecha >= fecha_desde,
                        columna_fecha <= fecha_hasta
                    ).all()
                    
                    ventas_a_eliminar = []
                    for v in ventas_mes:
                        if v.numero_proceso and v.numero_proceso.startswith(prefijo):
                            try:
                                sufijo = int(v.numero_proceso[4:])
                                if corr_desde <= sufijo <= corr_hasta:
                                    ventas_a_eliminar.append(v)
                            except ValueError:
                                pass
                                
                    if not ventas_a_eliminar:
                        QMessageBox.information(self, "Aviso", "No se encontraron ventas en ese rango de correlativos para el mes seleccionado.")
                        return
                        
                    count = len(ventas_a_eliminar)
                    confirm2 = QMessageBox.question(self, "Confirmar", f"Se encontraron {count} ventas en el mes seleccionado.\n¿Proceder a eliminar?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                    if confirm2 == QMessageBox.StandardButton.Yes:
                        eliminados = 0
                        errores = []
                        for v in ventas_a_eliminar:
                            try:
                                self.ventas_manager.eliminar_venta(v.id)
                                eliminados += 1
                            except Exception as e:
                                errores.append(f"{v.numero_proceso}: {str(e)}")
                                
                        self.session.commit()
                        
                        msg = f"Se eliminaron {eliminados} ventas."
                        if errores:
                            msg += f"\nHubo {len(errores)} errores:\n" + "\n".join(errores[:5])
                            if len(errores) > 5: msg += "\n..."
                            
                        QMessageBox.information(self, "Resultado", msg)
                        self.cargar_ventas()
                        self.recargar_filtro_clientes()

                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error al eliminar rango:\n{str(e)}")

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