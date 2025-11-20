"""
Gestión de Ajustes de Inventario - Sistema Kardex Valorizado
Archivo: src/views/ajustes_inventario_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox,
                             QTextEdit, QMessageBox, QDialog, QFormLayout,
                             QHeaderView, QGroupBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from sqlalchemy import extract
from sqlalchemy.orm import joinedload

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, AjusteInventario, AjusteInventarioDetalle,
                                   Producto, Almacen, Empresa, MotivoAjuste, TipoAjuste,
                                   MovimientoStock, TipoMovimiento)
from utils.widgets import UpperLineEdit, SearchableComboBox, MoneyDelegate
from utils.app_context import app_context
from utils.button_utils import style_button
from utils.kardex_manager import KardexManager
from views.motivos_ajuste_window import MotivoAjusteDialog

class AjusteInventarioDialog(QDialog):
    def __init__(self, parent=None, user_info=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.user_info = user_info
        self.detalles_ajuste = []
        self.selected_year = app_context.get_selected_year()
        self.kardex_manager = KardexManager(self.session)
        self.init_ui()
        self.cargar_datos_iniciales()

    def init_ui(self):
        self.setWindowTitle("Nuevo Ajuste de Inventario")
        self.setMinimumSize(1000, 650)
        layout = QVBoxLayout(self)

        titulo = QLabel("⚙️ Nuevo Ajuste de Inventario")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(titulo)

        grupo_ajuste = QGroupBox("Datos del Ajuste")
        form_ajuste = QFormLayout()

        fila1 = QHBoxLayout()
        self.cmb_tipo_ajuste = QComboBox()
        self.cmb_tipo_ajuste.addItems([e.value for e in TipoAjuste])
        self.cmb_tipo_ajuste.currentIndexChanged.connect(self.tipo_ajuste_cambiado)
        self.date_fecha = QDateEdit(calendarPopup=True, date=QDate.currentDate())
        self.txt_numero = UpperLineEdit(readOnly=True, styleSheet="background-color: #f0f0f0;")
        fila1.addWidget(QLabel("Tipo de Ajuste:"))
        fila1.addWidget(self.cmb_tipo_ajuste)
        fila1.addWidget(QLabel("Fecha:"))
        fila1.addWidget(self.date_fecha)
        fila1.addWidget(QLabel("Número:"))
        fila1.addWidget(self.txt_numero)
        form_ajuste.addRow(fila1)

        motivo_layout = QHBoxLayout()
        self.cmb_motivo = SearchableComboBox()
        btn_nuevo_motivo = QPushButton("Nuevo")
        btn_nuevo_motivo.clicked.connect(self.nuevo_motivo)
        motivo_layout.addWidget(self.cmb_motivo)
        motivo_layout.addWidget(btn_nuevo_motivo)
        form_ajuste.addRow("Motivo:*", motivo_layout)

        grupo_ajuste.setLayout(form_ajuste)
        layout.addWidget(grupo_ajuste)

        grupo_productos = QGroupBox("Productos")
        productos_layout = QVBoxLayout()
        selector_layout = QHBoxLayout()
        self.cmb_producto = SearchableComboBox()
        self.cmb_almacen = SearchableComboBox()
        self.spn_cantidad = QDoubleSpinBox(decimals=2, value=1.00)
        self.spn_cantidad.setRange(0.01, 999999)
        self.lbl_costo_unitario = QLabel("Costo Unit.:")
        self.spn_costo_unitario = QDoubleSpinBox(decimals=6)
        self.spn_costo_unitario.setRange(0.00, 999999.999999)
        btn_agregar = QPushButton("Agregar")
        btn_agregar.clicked.connect(self.agregar_producto)
        selector_layout.addWidget(QLabel("Producto:"))
        selector_layout.addWidget(self.cmb_producto, 2)
        selector_layout.addWidget(QLabel("Almacén:"))
        selector_layout.addWidget(self.cmb_almacen, 1)
        selector_layout.addWidget(QLabel("Cantidad:"))
        selector_layout.addWidget(self.spn_cantidad)
        selector_layout.addWidget(self.lbl_costo_unitario)
        selector_layout.addWidget(self.spn_costo_unitario)
        selector_layout.addWidget(btn_agregar)
        productos_layout.addLayout(selector_layout)

        self.tabla_productos = QTableWidget(columnCount=6)
        self.tabla_productos.setHorizontalHeaderLabels(["Producto", "Almacén", "Cantidad", "Costo Unit.", "Costo Total", "Acción"])

        money_delegate = MoneyDelegate(self.tabla_productos)
        self.tabla_productos.setItemDelegateForColumn(2, money_delegate)
        self.tabla_productos.setItemDelegateForColumn(3, money_delegate)
        self.tabla_productos.setItemDelegateForColumn(4, money_delegate)

        productos_layout.addWidget(self.tabla_productos)
        grupo_productos.setLayout(productos_layout)
        layout.addWidget(grupo_productos)

        self.txt_observaciones = QTextEdit(placeholderText="Observaciones adicionales...")
        layout.addWidget(QLabel("Observaciones:"))
        layout.addWidget(self.txt_observaciones)

        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar", clicked=self.reject)
        self.btn_guardar = QPushButton("Guardar Ajuste", clicked=self.guardar_ajuste)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        layout.addLayout(btn_layout)

    def cargar_datos_iniciales(self):
        productos = self.session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
        for prod in productos: self.cmb_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)
        almacenes = self.session.query(Almacen).filter_by(activo=True).order_by(Almacen.nombre).all()
        for alm in almacenes: self.cmb_almacen.addItem(alm.nombre, alm.id)
        self.generar_numero()
        self.tipo_ajuste_cambiado()

    def tipo_ajuste_cambiado(self):
        es_ingreso = self.cmb_tipo_ajuste.currentText() == TipoAjuste.INGRESO.value
        self.lbl_costo_unitario.setVisible(es_ingreso)
        self.spn_costo_unitario.setVisible(es_ingreso)
        self.cmb_motivo.clear()
        tipo_seleccionado = TipoAjuste(self.cmb_tipo_ajuste.currentText())
        motivos = self.session.query(MotivoAjuste).filter_by(activo=True, tipo=tipo_seleccionado).order_by(MotivoAjuste.nombre).all()
        for m in motivos: self.cmb_motivo.addItem(m.nombre, m.id)

    def generar_numero(self):
        ultimo = self.session.query(AjusteInventario).order_by(AjusteInventario.id.desc()).first()
        numero = int(ultimo.numero_ajuste.split('-')[1]) + 1 if ultimo and ultimo.numero_ajuste.startswith("AJU-") else 1
        self.txt_numero.setText(f"AJU-{numero:06d}")

    def nuevo_motivo(self):
        dialog = MotivoAjusteDialog(self, session=self.session)
        if dialog.exec(): self.tipo_ajuste_cambiado()

    def agregar_producto(self):
        prod_id, alm_id, cantidad = self.cmb_producto.currentData(), self.cmb_almacen.currentData(), self.spn_cantidad.value()
        if not all([prod_id, alm_id, cantidad > 0]):
            QMessageBox.warning(self, "Error", "Seleccione producto, almacén y cantidad válida.")
            return

        es_ingreso = self.cmb_tipo_ajuste.currentText() == TipoAjuste.INGRESO.value
        costo_unitario = 0
        if es_ingreso:
            costo_unitario = self.spn_costo_unitario.value()
            if costo_unitario <= 0:
                QMessageBox.warning(self, "Error", "El costo unitario para un ingreso debe ser mayor a cero.")
                return
        else:
            almacen = self.session.get(Almacen, alm_id)
            costo_unitario, _ = self.kardex_manager.calcular_costo_salida(almacen.empresa_id, prod_id, alm_id, cantidad)

        producto = self.session.get(Producto, prod_id)
        almacen = self.session.get(Almacen, alm_id)

        self.detalles_ajuste.append({
            'producto_id': prod_id, 'producto_nombre': f"{producto.codigo} - {producto.nombre}",
            'almacen_id': alm_id, 'almacen_nombre': almacen.nombre,
            'cantidad': cantidad, 'costo_unitario': costo_unitario, 'costo_total': cantidad * costo_unitario
        })
        self.actualizar_tabla_productos()

    def actualizar_tabla_productos(self):
        self.tabla_productos.setRowCount(len(self.detalles_ajuste))
        for row, det in enumerate(self.detalles_ajuste):
            self.tabla_productos.setItem(row, 0, QTableWidgetItem(det['producto_nombre']))
            self.tabla_productos.setItem(row, 1, QTableWidgetItem(det['almacen_nombre']))
            self.tabla_productos.setItem(row, 2, QTableWidgetItem(f"{det['cantidad']:,.2f}"))
            self.tabla_productos.setItem(row, 3, QTableWidgetItem(f"{det['costo_unitario']:.6f}"))
            self.tabla_productos.setItem(row, 4, QTableWidgetItem(f"{det['costo_total']:,.2f}"))
            btn_eliminar = QPushButton("✕", clicked=lambda _, r=row: self.eliminar_producto(r))
            self.tabla_productos.setCellWidget(row, 5, btn_eliminar)

    def eliminar_producto(self, row):
        del self.detalles_ajuste[row]
        self.actualizar_tabla_productos()

    def guardar_ajuste(self):
        if not self.cmb_motivo.currentData() or not self.detalles_ajuste:
            QMessageBox.warning(self, "Error", "Seleccione un motivo y agregue al menos un producto.")
            return

        try:
            ajuste = AjusteInventario(
                motivo_id=self.cmb_motivo.currentData(),
                numero_ajuste=self.txt_numero.text(),
                tipo=TipoAjuste(self.cmb_tipo_ajuste.currentText()),
                fecha=self.date_fecha.date().toPyDate(),
                observaciones=self.txt_observaciones.toPlainText().strip()
            )
            self.session.add(ajuste)
            self.session.flush()

            for det in self.detalles_ajuste:
                self.crear_detalle_y_movimiento(ajuste, det)

            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar el ajuste:\n{e}")

    def crear_detalle_y_movimiento(self, ajuste, det_dict):
        es_ingreso = ajuste.tipo == TipoAjuste.INGRESO
        self.session.add(AjusteInventarioDetalle(
            ajuste_id=ajuste.id, producto_id=det_dict['producto_id'],
            almacen_id=det_dict['almacen_id'], cantidad=det_dict['cantidad'],
            costo_unitario=det_dict['costo_unitario'] if es_ingreso else None
        ))
        almacen = self.session.get(Almacen, det_dict['almacen_id'])
        self.kardex_manager.registrar_movimiento(
            empresa_id=almacen.empresa_id, producto_id=det_dict['producto_id'], almacen_id=det_dict['almacen_id'],
            tipo=TipoMovimiento.AJUSTE_POSITIVO if es_ingreso else TipoMovimiento.AJUSTE_NEGATIVO,
            cantidad_entrada=det_dict['cantidad'] if es_ingreso else 0,
            cantidad_salida=det_dict['cantidad'] if not es_ingreso else 0,
            costo_unitario=det_dict['costo_unitario'], costo_total=det_dict['costo_total'],
            numero_documento=ajuste.numero_ajuste, fecha_documento=ajuste.fecha,
            motivo_ajuste_id=ajuste.motivo_id
        )

class AjustesInventarioWindow(QWidget):
    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.init_ui()
        self.cargar_ajustes()

    def init_ui(self):
        self.setWindowTitle("Gestión de Ajustes de Inventario")
        layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        titulo = QLabel("⚙️ Gestión de Ajustes de Inventario")
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        btn_nuevo = QPushButton("Nuevo Ajuste", clicked=self.nuevo_ajuste)
        header_layout.addWidget(btn_nuevo)
        layout.addLayout(header_layout)
        self.tabla = QTableWidget(columnCount=6)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Número", "Tipo", "Motivo", "Productos", "Acciones"])
        layout.addWidget(self.tabla)

    def cargar_ajustes(self):
        self.session.expire_all()
        ajustes = self.session.query(AjusteInventario).options(joinedload(AjusteInventario.motivo), joinedload(AjusteInventario.detalles)).order_by(AjusteInventario.id.desc()).all()
        self.tabla.setRowCount(len(ajustes))
        for row, ajuste in enumerate(ajustes):
            self.tabla.setItem(row, 0, QTableWidgetItem(ajuste.fecha.strftime('%d/%m/%Y')))
            self.tabla.setItem(row, 1, QTableWidgetItem(ajuste.numero_ajuste))
            self.tabla.setItem(row, 2, QTableWidgetItem(ajuste.tipo.value))
            self.tabla.setItem(row, 3, QTableWidgetItem(ajuste.motivo.nombre))
            self.tabla.setItem(row, 4, QTableWidgetItem(str(len(ajuste.detalles))))
            btn_eliminar = QPushButton("Eliminar", clicked=lambda _, a=ajuste: self.eliminar_ajuste(a))
            celda = QWidget()
            layout_celda = QHBoxLayout(celda)
            layout_celda.addWidget(btn_eliminar)
            layout_celda.setContentsMargins(0,0,0,0)
            self.tabla.setCellWidget(row, 5, celda)

    def nuevo_ajuste(self):
        dialog = AjusteInventarioDialog(self, self.user_info)
        if dialog.exec() == QDialog.DialogCode.Accepted: self.cargar_ajustes()

    def eliminar_ajuste(self, ajuste):
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar el ajuste '{ajuste.numero_ajuste}'?") != QMessageBox.StandardButton.Yes:
            return
        try:
            for detalle in ajuste.detalles:
                tipo_reversion = TipoMovimiento.AJUSTE_NEGATIVO if ajuste.tipo == TipoAjuste.INGRESO else TipoMovimiento.AJUSTE_POSITIVO
                mov_original = self.session.query(MovimientoStock).filter_by(numero_documento=ajuste.numero_ajuste, producto_id=detalle.producto_id, almacen_id=detalle.almacen_id).first()
                self.kardex_manager.registrar_movimiento(
                    empresa_id=self.session.get(Almacen, detalle.almacen_id).empresa_id,
                    producto_id=detalle.producto_id, almacen_id=detalle.almacen_id,
                    tipo=tipo_reversion,
                    cantidad_entrada=detalle.cantidad if tipo_reversion == TipoMovimiento.AJUSTE_POSITIVO else 0,
                    cantidad_salida=detalle.cantidad if tipo_reversion == TipoMovimiento.AJUSTE_NEGATIVO else 0,
                    costo_unitario=mov_original.costo_unitario if mov_original else 0,
                    costo_total=mov_original.costo_total if mov_original else 0,
                    numero_documento=ajuste.numero_ajuste, fecha_documento=ajuste.fecha,
                    observaciones=f"Reversión de ajuste {ajuste.numero_ajuste}"
                )
            self.session.delete(self.session.get(AjusteInventario, ajuste.id))
            self.session.commit()
            self.cargar_ajustes()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = AjustesInventarioWindow()
    ventana.show()
    sys.exit(app.exec())
