"""
Gestión de Tipo de Cambio - Sistema Kardex Valorizado
Archivo: src/views/tipo_cambio_window.py
(Versión mejorada con Soft Delete)
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QDateEdit, QDoubleSpinBox, QMessageBox, 
                             QDialog, QFormLayout, QHeaderView, QFileDialog)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from datetime import datetime, date
import openpyxl
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, TipoCambio


class TipoCambioDialog(QDialog):
    """Diálogo para crear/editar tipo de cambio"""
    
    def __init__(self, parent=None, tipo_cambio=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.tipo_cambio = tipo_cambio
        self.init_ui()
        
        if tipo_cambio:
            self.cargar_datos()
    
    def init_ui(self):
        self.setWindowTitle("Nuevo Tipo de Cambio" if not self.tipo_cambio else "Editar Tipo de Cambio")
        self.setFixedSize(450, 300)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel { color: #333; font-size: 11px; }
            QDateEdit, QDoubleSpinBox {
                padding: 8px; border: 2px solid #ddd;
                border-radius: 4px; background-color: white;
                font-size: 11px;
            }
            QDateEdit:focus, QDoubleSpinBox:focus { border: 2px solid #1a73e8; }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        titulo = QLabel("💱 " + ("Nuevo Tipo de Cambio" if not self.tipo_cambio else "Editar Tipo de Cambio"))
        titulo.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.date_fecha = QDateEdit()
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.setDate(QDate.currentDate())
        self.date_fecha.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Fecha:*", self.date_fecha)
        
        self.spn_compra = QDoubleSpinBox()
        self.spn_compra.setRange(0.001, 99.999)
        self.spn_compra.setDecimals(3)
        self.spn_compra.setSingleStep(0.001)
        self.spn_compra.setPrefix("S/ ")
        form_layout.addRow("Precio Compra:*", self.spn_compra)
        
        self.spn_venta = QDoubleSpinBox()
        self.spn_venta.setRange(0.001, 99.999)
        self.spn_venta.setDecimals(3)
        self.spn_venta.setSingleStep(0.001)
        self.spn_venta.setPrefix("S/ ")
        form_layout.addRow("Precio Venta:*", self.spn_venta)
        
        layout.addLayout(form_layout)
        
        nota = QLabel("ℹ️ El precio de venta se usa para conversión de dólares a soles")
        nota.setStyleSheet("color: #666; font-size: 10px; font-style: italic; padding: 10px;")
        nota.setWordWrap(True)
        layout.addWidget(nota)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("QPushButton { background-color: #f1f3f4; color: #333; padding: 10px 30px; border: none; border-radius: 5px; font-weight: bold; }")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("QPushButton { background-color: #1a73e8; color: white; padding: 10px 30px; border: none; border-radius: 5px; font-weight: bold; }")
        btn_guardar.clicked.connect(self.guardar)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def cargar_datos(self):
        """Carga datos del tipo de cambio en edición"""
        self.date_fecha.setDate(QDate(
            self.tipo_cambio.fecha.year,
            self.tipo_cambio.fecha.month,
            self.tipo_cambio.fecha.day
        ))
        self.date_fecha.setEnabled(False)  # No se puede cambiar la fecha
        
        self.spn_compra.setValue(self.tipo_cambio.precio_compra)
        self.spn_venta.setValue(self.tipo_cambio.precio_venta)
    
    def guardar(self):
        """Guarda el tipo de cambio"""
        fecha = self.date_fecha.date().toPyDate()
        precio_compra = self.spn_compra.value()
        precio_venta = self.spn_venta.value()
        
        if precio_compra <= 0 or precio_venta <= 0:
            QMessageBox.warning(self, "Error", "Los precios deben ser mayores a cero")
            return
        
        if precio_venta < precio_compra:
            respuesta = QMessageBox.question(
                self, "Confirmar",
                "⚠️ El precio de venta es menor que el de compra.\n¿Está seguro?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if respuesta == QMessageBox.StandardButton.No:
                return
        
        try:
            if not self.tipo_cambio:
                # --- MEJORA 1: Verificar que no exista uno ACTIVO para esa fecha ---
                existe = self.session.query(TipoCambio).filter_by(
                    fecha=fecha, 
                    activo=True
                ).first()
                
                if existe:
                    QMessageBox.warning(
                        self, "Error",
                        f"Ya existe tipo de cambio activo para {fecha.strftime('%d/%m/%Y')}"
                    )
                    return
                
                tc = TipoCambio(
                    fecha=fecha,
                    precio_compra=precio_compra,
                    precio_venta=precio_venta
                    # activo=True es el default en el modelo (asumiendo)
                )
                
                self.session.add(tc)
                mensaje = "Tipo de cambio registrado exitosamente"
            else:
                self.tipo_cambio = self.session.merge(self.tipo_cambio) # Asegurarse de que esté en sesión
                self.tipo_cambio.precio_compra = precio_compra
                self.tipo_cambio.precio_venta = precio_venta
                mensaje = "Tipo de cambio actualizado exitosamente"
            
            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")
        finally:
            self.session.close() # Cerrar sesión del diálogo

    def reject(self):
        """Cierra la sesión de la base de datos al cancelar."""
        self.session.close()
        super().reject()


class TipoCambioWindow(QWidget):
    """Ventana principal de gestión de tipo de cambio"""
    
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.cargar_tipos_cambio()
    
    def init_ui(self):
        self.setWindowTitle("Gestión de Tipo de Cambio")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("💱 Gestión de Tipo de Cambio (USD)")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        btn_nuevo = QPushButton("+ Nuevo")
        btn_nuevo.setStyleSheet("QPushButton { background-color: #1a73e8; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #1557b0; }")
        btn_nuevo.clicked.connect(self.nuevo_tipo_cambio)
        
        btn_importar = QPushButton("📥 Importar Excel")
        btn_importar.setStyleSheet("QPushButton { background-color: #34a853; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #2d8e47; }")
        btn_importar.clicked.connect(self.importar_excel)
        
        btn_plantilla = QPushButton("📋 Descargar Plantilla")
        btn_plantilla.setStyleSheet("QPushButton { background-color: #f9ab00; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-weight: bold; }")
        btn_plantilla.clicked.connect(self.descargar_plantilla)
        
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_plantilla)
        header_layout.addWidget(btn_importar)
        header_layout.addWidget(btn_nuevo)
        
        # Filtros
        filtro_layout = QHBoxLayout()
        
        lbl_desde = QLabel("Desde:")
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))
        self.date_desde.setDisplayFormat("dd/MM/yyyy")
        self.date_desde.dateChanged.connect(self.cargar_tipos_cambio)
        
        lbl_hasta = QLabel("Hasta:")
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDate(QDate.currentDate())
        self.date_hasta.setDisplayFormat("dd/MM/yyyy")
        self.date_hasta.dateChanged.connect(self.cargar_tipos_cambio)
        
        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.clicked.connect(self.cargar_tipos_cambio)
        
        filtro_layout.addWidget(lbl_desde)
        filtro_layout.addWidget(self.date_desde)
        filtro_layout.addWidget(lbl_hasta)
        filtro_layout.addWidget(self.date_hasta)
        filtro_layout.addWidget(btn_actualizar)
        filtro_layout.addStretch()
        
        self.lbl_contador = QLabel()
        self.lbl_contador.setStyleSheet("color: #666; font-size: 11px;")
        
        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Precio Compra", "Precio Venta", "Acciones"])
        
        self.tabla.setStyleSheet("""
            QTableWidget { border: 1px solid #ddd; border-radius: 5px; background-color: white; }
            QHeaderView::section { background-color: #f1f3f4; padding: 10px;
                border: none; font-weight: bold; }
        """)
        
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(3, 150)
        
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addLayout(header_layout)
        layout.addLayout(filtro_layout)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)
        
        self.setLayout(layout)
    
    def cargar_tipos_cambio(self):
        """Carga tipos de cambio en el rango de fechas"""
        fecha_desde = self.date_desde.date().toPyDate()
        fecha_hasta = self.date_hasta.date().toPyDate()
        
        try:
            # --- MEJORA 2: Filtrar solo los activos ---
            tipos_cambio = self.session.query(TipoCambio).filter(
                TipoCambio.fecha >= fecha_desde,
                TipoCambio.fecha <= fecha_hasta,
                TipoCambio.activo == True  # <-- FILTRO AÑADIDO
            ).order_by(TipoCambio.fecha.desc()).all()
            
            self.mostrar_tipos_cambio(tipos_cambio)
            
        except Exception as e:
            QMessageBox.critical(self, "Error de Carga", f"Error al consultar la base de datos:\n{e}")
            self.session.rollback()

    
    def mostrar_tipos_cambio(self, tipos_cambio):
        """Muestra tipos de cambio en la tabla"""
        self.tabla.setRowCount(len(tipos_cambio))
        
        for row, tc in enumerate(tipos_cambio):
            item_fecha = QTableWidgetItem(tc.fecha.strftime('%d/%m/%Y'))
            item_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(row, 0, item_fecha)
            
            item_compra = QTableWidgetItem(f"S/ {tc.precio_compra:.3f}")
            item_compra.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 1, item_compra)
            
            item_venta = QTableWidgetItem(f"S/ {tc.precio_venta:.3f}")
            item_venta.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 2, item_venta)
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 5, 5, 5)
            
            btn_editar = QPushButton("Editar")
            btn_editar.setStyleSheet("QPushButton { background-color: #34a853; color: white; padding: 5px 10px; border: none; border-radius: 3px; }")
            btn_editar.clicked.connect(lambda checked, t=tc: self.editar_tipo_cambio(t))
            
            btn_eliminar = QPushButton("Eliminar")
            btn_eliminar.setStyleSheet("QPushButton { background-color: #ea4335; color: white; padding: 5px 10px; border: none; border-radius: 3px; }")
            btn_eliminar.clicked.connect(lambda checked, t=tc: self.eliminar_tipo_cambio(t))
            
            btn_layout.addWidget(btn_editar)
            btn_layout.addWidget(btn_eliminar)
            btn_widget.setLayout(btn_layout)
            
            self.tabla.setCellWidget(row, 3, btn_widget)
        
        self.lbl_contador.setText(f"📊 Total: {len(tipos_cambio)} registro(s) activos")
    
    def nuevo_tipo_cambio(self):
        """Abre diálogo para crear tipo de cambio"""
        dialog = TipoCambioDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_tipos_cambio()
    
    def editar_tipo_cambio(self, tipo_cambio):
        """Abre diálogo para editar tipo de cambio"""
        dialog = TipoCambioDialog(self, tipo_cambio)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(tipo_cambio)
            self.cargar_tipos_cambio()
    
    def eliminar_tipo_cambio(self, tipo_cambio):
        """Elimina (desactiva) un tipo de cambio"""
        respuesta = QMessageBox.question(
            self,
            "Confirmar desactivación",
            f"¿Desactivar tipo de cambio del {tipo_cambio.fecha.strftime('%d/%m/%Y')}?\n"
            "El registro no se borrará, solo se ocultará.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                # --- MEJORA 3: Usar Soft Delete ---
                tc_a_eliminar = self.session.merge(tipo_cambio)
                tc_a_eliminar.activo = False
                # self.session.delete(tipo_cambio) <-- REEMPLAZADO
                # --- FIN MEJORA ---
                
                self.session.commit()
                QMessageBox.information(self, "Éxito", "Tipo de cambio desactivado")
                self.cargar_tipos_cambio()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error al desactivar:\n{str(e)}")
    
    def descargar_plantilla(self):
        # ... (código sin cambios)
        archivo, _ = QFileDialog.getSaveFileName(
            self, "Guardar Plantilla", "plantilla_tipo_cambio.xlsx", "Excel (*.xlsx)"
        )
        if not archivo: return
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "TipoCambio"
            headers = ['fecha', 'precio_compra', 'precio_venta']
            ws.append(headers)
            ws.append(['2024-01-15', 3.850, 3.870])
            for cell in ws[1]:
                cell.font = openpyxl.styles.Font(bold=True)
            wb.save(archivo)
            QMessageBox.information(self, "Éxito", f"Plantilla descargada:\n{archivo}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar plantilla:\n{str(e)}")
    
    def importar_excel(self):
        """Importa tipos de cambio desde Excel"""
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo Excel", "", "Excel (*.xlsx *.xls)"
        )
        if not archivo: return
        
        try:
            wb = openpyxl.load_workbook(archivo)
            ws = wb.active
            
            nuevos = 0
            actualizados = 0
            errores = []
            
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    if not row[0] or not row[1] or not row[2]:
                        continue
                    
                    if isinstance(row[0], datetime): fecha = row[0].date()
                    elif isinstance(row[0], date): fecha = row[0]
                    else: fecha = datetime.strptime(str(row[0]), '%Y-%m-%d').date()
                    
                    precio_compra = float(row[1])
                    precio_venta = float(row[2])
                    
                    # --- MEJORA 4: Buscar CUALQUIERA (activo o inactivo) para reactivarlo ---
                    tc_existe = self.session.query(TipoCambio).filter_by(fecha=fecha).first()
                    
                    if tc_existe:
                        tc_existe.precio_compra = precio_compra
                        tc_existe.precio_venta = precio_venta
                        tc_existe.activo = True # <-- Reactivarlo si se importa
                        actualizados += 1
                    else:
                        tc_nuevo = TipoCambio(
                            fecha=fecha,
                            precio_compra=precio_compra,
                            precio_venta=precio_venta
                        )
                        self.session.add(tc_nuevo)
                        nuevos += 1
                        
                except Exception as e:
                    errores.append(f"Fila {row_idx}: {str(e)}")
            
            self.session.commit()
            
            mensaje = f"✓ Importación exitosa:\n{nuevos} nuevos\n{actualizados} actualizados/reactivados"
            if errores:
                mensaje += f"\n\n⚠️ {len(errores)} errores:\n" + "\n".join(errores[:5])
            
            QMessageBox.information(self, "Importación", mensaje)
            self.cargar_tipos_cambio()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al importar:\n{str(e)}")


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    # --- Asumiendo que tu modelo TipoCambio tiene la columna 'activo' ---
    # from models.database_model import Base, engine, Column, Boolean
    # 
    # class TipoCambio(Base):
    #     __tablename__ = 'tipo_cambio'
    #     # ... otras columnas ...
    #     activo = Column(Boolean, default=True, nullable=False)
    #
    # Base.metadata.create_all(engine)
    # -----------------------------------------------------------------
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    ventana = TipoCambioWindow()
    ventana.resize(900, 600)
    ventana.show()
    
    sys.exit(app.exec())