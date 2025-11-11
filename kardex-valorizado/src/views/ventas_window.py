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

from .productos_window import ProductoDialog
try:
    from .clientes_window import ClienteDialog
except ImportError:
    ClienteDialog = None

from models.database_model import (obtener_session, Venta, VentaDetalle,
                                   Cliente, Producto, Almacen, Empresa,
                                   TipoCambio, TipoDocumento, Moneda, SerieCorrelativo,
                                   MovimientoStock, TipoMovimiento)
from utils.widgets import UppercaseValidator, SearchableComboBox
from utils.app_context import app_context
from utils.validation import verificar_estado_anio, AnioCerradoError
from utils.button_utils import style_button
from utils.kardex_manager import KardexManager

class SelectAllLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(UppercaseValidator())
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()

class SelectAllSpinBox(QDoubleSpinBox):
    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)

class VentaDialog(QDialog):
    def __init__(self, parent=None, user_info=None, venta_a_editar=None, detalles_originales=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.user_info = user_info
        self.venta_original = venta_a_editar
        self.detalles_originales_obj = detalles_originales
        self.detalles_venta = []
        self.lista_completa_productos = []
        self.kardex_manager = KardexManager(self.session)
        self.init_ui()
        self.cargar_datos_iniciales()
        if self.venta_original:
            self.cargar_datos_para_edicion()

    def init_ui(self):
        self.setWindowTitle("Registrar Venta")
        self.setMinimumSize(1500, 800)
        layout = QVBoxLayout(self)
        titulo = QLabel("📦 Nueva Venta")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(titulo)

        style_cuadrado_verde = """QPushButton { background-color: #34a853; color: white; font-weight: bold; font-size: 16px; border-radius: 5px; padding: 0px; } QPushButton:hover { background-color: #2e8b4e; }"""

        grupo_venta = QGroupBox("Datos de la Venta")
        form_venta = QFormLayout()

        fila_cliente_proceso = QHBoxLayout()
        fila_cliente_proceso.addWidget(QLabel("Cliente:*"))
        self.cmb_cliente = SearchableComboBox()
        self.cmb_cliente.currentIndexChanged.connect(self.cliente_seleccionado)
        fila_cliente_proceso.addWidget(self.cmb_cliente, 2)
        self.btn_nuevo_cliente = QPushButton("+", toolTip="Crear nuevo cliente", clicked=self.crear_nuevo_cliente)
        self.btn_nuevo_cliente.setFixedSize(30, 30)
        self.btn_nuevo_cliente.setStyleSheet(style_cuadrado_verde)
        fila_cliente_proceso.addWidget(self.btn_nuevo_cliente)
        fila_cliente_proceso.addSpacing(15)
        fila_cliente_proceso.addWidget(QLabel("Nro. Proceso:*"))
        self.txt_numero_proceso = SelectAllLineEdit(placeholderText="Ej: 1 (se autocompletará)", toolTip="Ingrese el correlativo. El formato 05MMNNNNNN se generará automáticamente.")
        fila_cliente_proceso.addWidget(self.txt_numero_proceso, 1)

        layout_fila1_completa = QVBoxLayout()
        layout_fila1_completa.addLayout(fila_cliente_proceso)
        self.lbl_cliente_info = QLabel()
        layout_fila1_completa.addWidget(self.lbl_cliente_info)
        form_venta.addRow(layout_fila1_completa)

        # ... (Resto de la UI)
        grupo_venta.setLayout(form_venta)
        layout.addWidget(grupo_venta)
        self.setLayout(layout)

    def cargar_datos_iniciales(self):
        # Carga clientes, productos, almacenes...
        pass
    def cliente_seleccionado(self): pass
    def fecha_cambiada(self): pass
    def moneda_cambiada(self): pass
    def actualizar_tipo_cambio(self): pass
    def agregar_producto(self): pass
    def actualizar_tabla_productos(self): pass
    def eliminar_producto(self, row): pass
    def recalcular_totales(self): pass
    def _actualizar_calculos_igv(self): pass
    def _calcular_montos_decimal(self): pass
    def guardar_venta(self): pass
    def cargar_datos_para_edicion(self): pass
    def producto_en_detalle_editado(self, index, row): pass
    def detalle_editado(self, row, column): pass
    def sincronizar_fecha_contable(self, date): pass
    def formatear_numero_documento(self): pass
    def eventFilter(self, source, event): return super().eventFilter(source, event)
    def crear_nuevo_cliente(self): pass
    def crear_nuevo_producto(self): pass
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4: self.guardar_venta()
        else: super().keyPressEvent(event)

class DetalleVentaDialog(QDialog):
    def __init__(self, venta, detalles, session, parent=None):
        super().__init__(parent)
        # ... (UI de solo lectura)

class VentasWindow(QWidget):
    def __init__(self, user_info=None):
        super().__init__()
        self.session = obtener_session()
        self.user_info = user_info
        self.ventas_mostradas = []
        self.init_ui()
        self.cargar_ventas()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2: self.nueva_venta()
        elif event.key() == Qt.Key.Key_F6:
            fila = self.tabla.currentRow()
            if fila != -1: self.editar_venta(self.ventas_mostradas[fila])
        else: super().keyPressEvent(event)

    def init_ui(self):
        self.setWindowTitle("Gestión de Ventas")
        layout = QVBoxLayout(self)
        titulo = QLabel("📦 Gestión de Ventas")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(titulo)
        # ... (Resto de la UI principal)

    def cargar_ventas(self): pass
    def mostrar_ventas(self, ventas): pass

    def nueva_venta(self):
        dialog = VentaDialog(self, self.user_info)
        if dialog.exec() == QDialog.DialogCode.Accepted: self.cargar_ventas()

    def editar_venta(self, venta):
        detalles = self.session.query(VentaDetalle).filter_by(venta_id=venta.id).all()
        dialog = VentaDialog(self, self.user_info, venta_a_editar=venta, detalles_originales=detalles)
        if dialog.exec() == QDialog.DialogCode.Accepted: self.cargar_ventas()

    def ver_detalle_venta(self, venta):
        detalles = self.session.query(VentaDetalle).filter_by(venta_id=venta.id).all()
        dialog = DetalleVentaDialog(venta, detalles, self.session, self)
        dialog.exec()

    def eliminar_venta(self, venta):
        # ... (lógica de eliminación)
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentasWindow()
    ventana.show()
    sys.exit(app.exec())
