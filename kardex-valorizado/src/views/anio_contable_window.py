"""
Ventana de Administración de Años Contables
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from datetime import datetime, date
from sqlalchemy import extract, and_
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, AnioContable, EstadoAnio,
                                   MovimientoStock, TipoMovimiento, Producto, Almacen)
from utils.app_context import app_context

class AnioContableWindow(QWidget):
    """Ventana para gestionar los años contables."""

    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.cargar_anios()

    def init_ui(self):
        self.setWindowTitle("Administración de Años Contables")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Título
        titulo = QLabel("🗓️ Administración de Años Contables")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        layout.addWidget(titulo)

        # Tabla de años
        self.tabla_anios = QTableWidget()
        self.tabla_anios.setColumnCount(3)
        self.tabla_anios.setHorizontalHeaderLabels(["Año", "Estado", "Fecha de Creación"])
        self.tabla_anios.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_anios.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.tabla_anios.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.tabla_anios)

        # Botones de acción
        btn_layout = QHBoxLayout()

        self.btn_crear = QPushButton("➕ Crear Nuevo Año")
        self.btn_crear.clicked.connect(self.crear_nuevo_anio)

        self.btn_cerrar = QPushButton("🔒 Cerrar Año Seleccionado")
        self.btn_cerrar.clicked.connect(self.cerrar_anio)

        self.btn_reabrir = QPushButton("🔓 Reabrir Año Seleccionado")
        self.btn_reabrir.clicked.connect(self.reabrir_anio)

        btn_layout.addWidget(self.btn_crear)
        btn_layout.addWidget(self.btn_cerrar)
        btn_layout.addWidget(self.btn_reabrir)

        layout.addLayout(btn_layout)

    def cargar_anios(self):
        """Carga todos los años desde la base de datos a la tabla."""
        self.tabla_anios.setRowCount(0)
        anios = self.session.query(AnioContable).order_by(AnioContable.anio.desc()).all()

        self.tabla_anios.setRowCount(len(anios))

        for row, anio_obj in enumerate(anios):
            self.tabla_anios.setItem(row, 0, QTableWidgetItem(str(anio_obj.anio)))

            estado_item = QTableWidgetItem(anio_obj.estado.value)
            if anio_obj.estado == EstadoAnio.CERRADO:
                estado_item.setForeground(Qt.GlobalColor.gray)
            self.tabla_anios.setItem(row, 1, estado_item)

            self.tabla_anios.setItem(row, 2, QTableWidgetItem(anio_obj.fecha_registro.strftime('%d/%m/%Y %H:%M')))

    def crear_nuevo_anio(self):
        """Crea el siguiente año contable si no existe."""
        ultimo_anio_obj = self.session.query(AnioContable).order_by(AnioContable.anio.desc()).first()

        if ultimo_anio_obj:
            nuevo_anio_numero = ultimo_anio_obj.anio + 1
        else:
            nuevo_anio_numero = datetime.now().year

        confirmar = QMessageBox.question(self, "Confirmar Creación",
                                         f"¿Desea crear el año contable {nuevo_anio_numero}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirmar == QMessageBox.StandardButton.Yes:
            existente = self.session.query(AnioContable).filter_by(anio=nuevo_anio_numero).first()
            if existente:
                QMessageBox.warning(self, "Año Duplicado", f"El año {nuevo_anio_numero} ya existe.")
                return

            nuevo_anio = AnioContable(anio=nuevo_anio_numero, estado=EstadoAnio.ABIERTO)
            self.session.add(nuevo_anio)
            self.session.commit()

            QMessageBox.information(self, "Éxito", f"Año {nuevo_anio_numero} creado exitosamente.")
            self.cargar_anios()

    def cerrar_anio(self):
        selected_row = self.tabla_anios.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione un año de la tabla.")
            return

        anio_str = self.tabla_anios.item(selected_row, 0).text()
        anio_a_cerrar_obj = self.session.query(AnioContable).filter_by(anio=int(anio_str)).first()

        if anio_a_cerrar_obj.estado == EstadoAnio.CERRADO:
            QMessageBox.information(self, "Ya Cerrado", "El año seleccionado ya está cerrado.")
            return

        confirmar = QMessageBox.warning(self, "Confirmar Cierre de Año",
            f"¿Está seguro de que desea cerrar el año {anio_str}?\n\n"
            "Esta acción calculará los saldos finales y los transferirá como saldos iniciales al siguiente año. "
            "Una vez cerrado, no se podrán registrar nuevos movimientos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirmar == QMessageBox.StandardButton.No:
            return

        try:
            anio_numero = int(anio_str)
            anio_siguiente = anio_numero + 1

            # 1. Obtener saldos finales
            subquery = self.session.query(
                MovimientoStock.producto_id,
                MovimientoStock.almacen_id,
                func.max(MovimientoStock.id).label('max_id')
            ).filter(
                extract('year', MovimientoStock.fecha_documento) == anio_numero
            ).group_by(
                MovimientoStock.producto_id,
                MovimientoStock.almacen_id
            ).subquery()

            saldos_finales = self.session.query(MovimientoStock).join(
                subquery,
                MovimientoStock.id == subquery.c.max_id
            ).all()

            # 2. Asegurar que el año siguiente exista
            anio_siguiente_obj = self.session.query(AnioContable).filter_by(anio=anio_siguiente).first()
            if not anio_siguiente_obj:
                anio_siguiente_obj = AnioContable(anio=anio_siguiente, estado=EstadoAnio.ABIERTO)
                self.session.add(anio_siguiente_obj)

            # 3. Eliminar stock inicial previo del año siguiente para evitar duplicados
            self.session.query(MovimientoStock).filter(
                extract('year', MovimientoStock.fecha_documento) == anio_siguiente,
                MovimientoStock.tipo == TipoMovimiento.STOCK_INICIAL
            ).delete()

            # 4. Crear nuevos movimientos de stock inicial
            nuevos_movimientos = []
            for saldo in saldos_finales:
                if saldo.saldo_cantidad > 0:
                    costo_unitario_final = (Decimal(str(saldo.saldo_costo_total)) / Decimal(str(saldo.saldo_cantidad))).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)

                    nuevo_movimiento = MovimientoStock(
                        empresa_id=saldo.empresa_id,
                        producto_id=saldo.producto_id,
                        almacen_id=saldo.almacen_id,
                        tipo=TipoMovimiento.STOCK_INICIAL,
                        fecha_documento=date(anio_siguiente, 1, 1),
                        cantidad_entrada=saldo.saldo_cantidad,
                        cantidad_salida=0,
                        costo_unitario=float(costo_unitario_final),
                        costo_total=saldo.saldo_costo_total,
                        saldo_cantidad=saldo.saldo_cantidad,
                        saldo_costo_total=saldo.saldo_costo_total,
                        observaciones=f"Saldo inicial del año {anio_numero}"
                    )
                    nuevos_movimientos.append(nuevo_movimiento)

            self.session.add_all(nuevos_movimientos)

            # 5. Cerrar el año
            anio_a_cerrar_obj.estado = EstadoAnio.CERRADO
            self.session.commit()

            QMessageBox.information(self, "Éxito",
                f"El año {anio_str} ha sido cerrado exitosamente.\n"
                f"Se han generado {len(nuevos_movimientos)} registros de saldo inicial para el año {anio_siguiente}.")

            self.cargar_anios()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error en el Cierre", f"Ocurrió un error al cerrar el año:\n{str(e)}")


    def reabrir_anio(self):
        """Reabre un año que estaba cerrado."""
        selected_row = self.tabla_anios.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione un año de la tabla.")
            return

        anio_str = self.tabla_anios.item(selected_row, 0).text()
        anio_a_reabrir = self.session.query(AnioContable).filter_by(anio=int(anio_str)).first()

        if anio_a_reabrir.estado == EstadoAnio.ABIERTO:
            QMessageBox.information(self, "Ya Abierto", "El año seleccionado ya está abierto.")
            return

        confirmar = QMessageBox.question(self, "Confirmar Reapertura",
                                         f"¿Desea reabrir el año contable {anio_str}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirmar == QMessageBox.StandardButton.Yes:
            anio_a_reabrir.estado = EstadoAnio.ABIERTO
            self.session.commit()
            QMessageBox.information(self, "Éxito", f"El año {anio_str} ha sido reabierto.")
            self.cargar_anios()

    def closeEvent(self, event):
        """Asegura que la sesión de la base de datos se cierre al salir."""
        self.session.close()
        super().closeEvent(event)
