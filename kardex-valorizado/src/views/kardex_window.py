"""
Kardex Valorizado - Sistema Kardex Valorizado
Archivo: src/views/kardex_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QComboBox, QDateEdit, QMessageBox, QHeaderView,
                              QGroupBox, QRadioButton, QButtonGroup, QFileDialog)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from sqlalchemy import extract
from utils.app_context import app_context
import xlsxwriter

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, Producto, Empresa, Almacen,
                                   MovimientoStock, Moneda, MetodoValuacion)


class KardexWindow(QWidget):
    """Ventana de Kardex Valorizado"""
    
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.movimientos = []
        self.init_ui()
        self.cargar_empresas()
    
    def init_ui(self):
        self.setWindowTitle("Kardex Valorizado")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("📊 Kardex Valorizado")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        
        # === FILTROS ===
        grupo_filtros = QGroupBox("Filtros")
        filtros_layout = QVBoxLayout()
        
        # Fila 1: Empresa, Producto, Almacén
        fila1 = QHBoxLayout()
        
        fila1.addWidget(QLabel("Empresa:"))
        self.cmb_empresa = QComboBox()
        self.cmb_empresa.setMinimumWidth(200)
        self.cmb_empresa.currentIndexChanged.connect(self.empresa_cambiada)
        fila1.addWidget(self.cmb_empresa, 2)
        
        fila1.addWidget(QLabel("Producto:"))
        self.cmb_producto = QComboBox()
        self.cmb_producto.setMinimumWidth(300)
        fila1.addWidget(self.cmb_producto, 3)
        
        fila1.addWidget(QLabel("Almacén:"))
        self.cmb_almacen = QComboBox()
        self.cmb_almacen.addItem("Todos", None)
        fila1.addWidget(self.cmb_almacen, 1)
        
        filtros_layout.addLayout(fila1)
        
        # Fila 2: Fechas y Moneda
        fila2 = QHBoxLayout()
        
        fila2.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))
        self.date_desde.setDisplayFormat("dd/MM/yyyy")
        fila2.addWidget(self.date_desde)
        
        fila2.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDate(QDate.currentDate())
        self.date_hasta.setDisplayFormat("dd/MM/yyyy")
        fila2.addWidget(self.date_hasta)
        
        fila2.addWidget(QLabel("Moneda:"))
        self.cmb_moneda_vista = QComboBox()
        self.cmb_moneda_vista.addItem("Soles (S/)", "SOLES")
        self.cmb_moneda_vista.addItem("Dólares ($)", "DOLARES")
        fila2.addWidget(self.cmb_moneda_vista)
        
        # Vista
        fila2.addWidget(QLabel("Vista:"))
        self.cmb_vista = QComboBox()
        self.cmb_vista.addItem("Movimiento por Movimiento", "DETALLADO")
        self.cmb_vista.addItem("Saldos por Día", "CONSOLIDADO")
        fila2.addWidget(self.cmb_vista)
        
        fila2.addStretch()
        
        filtros_layout.addLayout(fila2)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        
        btn_generar = QPushButton("🔍 Generar Kardex")
        btn_generar.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)
        btn_generar.clicked.connect(self.generar_kardex)
        
        btn_exportar = QPushButton("📥 Exportar Excel")
        btn_exportar.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        btn_exportar.clicked.connect(self.exportar_excel)
        
        btn_layout.addWidget(btn_generar)
        btn_layout.addWidget(btn_exportar)
        btn_layout.addStretch()
        
        filtros_layout.addLayout(btn_layout)
        
        grupo_filtros.setLayout(filtros_layout)
        layout.addWidget(grupo_filtros)
        
        # Info método de valuación
        self.lbl_metodo = QLabel()
        self.lbl_metodo.setStyleSheet("""
            background-color: #e8f0fe;
            padding: 10px;
            border-radius: 5px;
            color: #1a73e8;
            font-weight: bold;
        """)
        layout.addWidget(self.lbl_metodo)
        
        # === TABLA KARDEX ===
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(11)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha", "Documento", "Detalle", 
            "Entrada Cant.", "Entrada C.U.", "Entrada Total",
            "Salida Cant.", "Salida C.U.", "Salida Total",
            "Saldo Cant.", "Saldo Total"
        ])
        
        self.tabla.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #1a73e8;
                color: white;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
        """)
        
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        self.tabla.setAlternatingRowColors(True)
        
        layout.addWidget(self.tabla)
        
        # Resumen
        self.lbl_resumen = QLabel()
        self.lbl_resumen.setStyleSheet("""
            background-color: #f1f3f4;
            padding: 15px;
            border-radius: 5px;
            font-size: 12px;
        """)
        layout.addWidget(self.lbl_resumen)
        
        self.setLayout(layout)
    
    def cargar_empresas(self):
        """Carga empresas activas"""
        empresas = self.session.query(Empresa).filter_by(activo=True).all()
        
        for emp in empresas:
            self.cmb_empresa.addItem(f"{emp.ruc} - {emp.razon_social}", emp.id)
    
    def empresa_cambiada(self):
        """Cuando cambia la empresa"""
        empresa_id = self.cmb_empresa.currentData()
        
        if not empresa_id:
            return
        
        empresa = self.session.query(Empresa).get(empresa_id)
        
        # Mostrar método de valuación
        metodo_texto = {
            MetodoValuacion.PEPS: "PEPS (Primero en Entrar, Primero en Salir)",
            MetodoValuacion.UEPS: "UEPS (Último en Entrar, Primero en Salir)",
            MetodoValuacion.PROMEDIO_PONDERADO: "Promedio Ponderado"
        }
        
        self.lbl_metodo.setText(f"📋 Método de Valuación: {metodo_texto[empresa.metodo_valuacion]}")
        
        # Cargar productos
        self.cmb_producto.clear()
        productos = self.session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
        
        for prod in productos:
            self.cmb_producto.addItem(f"{prod.codigo} - {prod.nombre}", prod.id)
        
        # Cargar almacenes
        self.cmb_almacen.clear()
        self.cmb_almacen.addItem("Todos los almacenes", None)
        
        almacenes = self.session.query(Almacen).filter_by(
            empresa_id=empresa_id,
            activo=True
        ).all()
        
        for alm in almacenes:
            self.cmb_almacen.addItem(alm.nombre, alm.id)
    
    def generar_kardex(self):
        """Genera el kardex valorizado"""
        empresa_id = self.cmb_empresa.currentData()
        producto_id = self.cmb_producto.currentData()
        almacen_id = self.cmb_almacen.currentData()
        
        if not empresa_id or not producto_id:
            QMessageBox.warning(self, "Error", "Seleccione empresa y producto")
            return
        
        fecha_desde = self.date_desde.date().toPyDate()
        fecha_hasta = self.date_hasta.date().toPyDate()
        
        # Obtener empresa y método
        empresa = self.session.query(Empresa).get(empresa_id)
        producto = self.session.query(Producto).get(producto_id)
        
        # Consultar movimientos
        query = self.session.query(MovimientoStock).filter(
            MovimientoStock.empresa_id == empresa_id,
            MovimientoStock.producto_id == producto_id,
            MovimientoStock.fecha_documento >= fecha_desde,
            MovimientoStock.fecha_documento <= fecha_hasta
        )
        
        if almacen_id:
            query = query.filter_by(almacen_id=almacen_id)
        
        self.movimientos = query.order_by(MovimientoStock.fecha_documento, MovimientoStock.id).all()
        
        if not self.movimientos:
            QMessageBox.information(self, "Sin datos", "No hay movimientos para los filtros seleccionados")
            self.tabla.setRowCount(0)
            return
        
        # Recalcular según método (esto es crítico)
        self.recalcular_kardex(empresa.metodo_valuacion, producto)
        
        # Mostrar en tabla
        self.mostrar_kardex()
    
    def recalcular_kardex(self, metodo, producto):
        """
        Recalcula el kardex según el método de valuación
        ESTE ES EL ALGORITMO MÁS IMPORTANTE DEL SISTEMA
        """
        if metodo == MetodoValuacion.PROMEDIO_PONDERADO:
            self.calcular_promedio_ponderado()
        elif metodo == MetodoValuacion.PEPS:
            self.calcular_peps()
        elif metodo == MetodoValuacion.UEPS:
            self.calcular_ueps()
    
    def calcular_promedio_ponderado(self):
        """Calcula kardex con método Promedio Ponderado"""
        saldo_cantidad = Decimal('0')
        saldo_valor = Decimal('0')
        
        for mov in self.movimientos:
            if mov.cantidad_entrada > 0:
                # Entrada: agregar al inventario
                saldo_cantidad += Decimal(str(mov.cantidad_entrada))
                saldo_valor += Decimal(str(mov.costo_total))
                
                # Calcular nuevo costo promedio
                if saldo_cantidad > 0:
                    costo_promedio = saldo_valor / saldo_cantidad
                else:
                    costo_promedio = Decimal('0')
                
                mov.costo_unitario_calculado = float(costo_promedio)
                mov.saldo_cantidad_calculado = float(saldo_cantidad)
                mov.saldo_valor_calculado = float(saldo_valor)
                
            else:
                # Salida: usar costo promedio actual
                if saldo_cantidad > 0:
                    costo_promedio = saldo_valor / saldo_cantidad
                else:
                    costo_promedio = Decimal('0')
                
                cantidad_salida = Decimal(str(mov.cantidad_salida))
                valor_salida = cantidad_salida * costo_promedio
                
                saldo_cantidad -= cantidad_salida
                saldo_valor -= valor_salida
                
                if saldo_cantidad < 0:
                    saldo_cantidad = Decimal('0')
                    saldo_valor = Decimal('0')
                
                mov.costo_unitario_calculado = float(costo_promedio)
                mov.costo_total_calculado = float(valor_salida)
                mov.saldo_cantidad_calculado = float(saldo_cantidad)
                mov.saldo_valor_calculado = float(saldo_valor)
    
    def calcular_peps(self):
        """Calcula kardex con método PEPS (FIFO)"""
        # Cola de lotes (los primeros en entrar)
        lotes = []
        
        for mov in self.movimientos:
            if mov.cantidad_entrada > 0:
                # Entrada: agregar nuevo lote
                lotes.append({
                    'cantidad': Decimal(str(mov.cantidad_entrada)),
                    'costo_unitario': Decimal(str(mov.costo_unitario))
                })
                
                mov.costo_unitario_calculado = float(mov.costo_unitario)
                
            else:
                # Salida: tomar de los primeros lotes
                cantidad_pendiente = Decimal(str(mov.cantidad_salida))
                costo_total_salida = Decimal('0')
                
                while cantidad_pendiente > 0 and lotes:
                    lote = lotes[0]
                    
                    if lote['cantidad'] <= cantidad_pendiente:
                        # Consumir lote completo
                        costo_total_salida += lote['cantidad'] * lote['costo_unitario']
                        cantidad_pendiente -= lote['cantidad']
                        lotes.pop(0)
                    else:
                        # Consumir parte del lote
                        costo_total_salida += cantidad_pendiente * lote['costo_unitario']
                        lote['cantidad'] -= cantidad_pendiente
                        cantidad_pendiente = Decimal('0')
                
                if mov.cantidad_salida > 0:
                    costo_promedio_salida = costo_total_salida / Decimal(str(mov.cantidad_salida))
                else:
                    costo_promedio_salida = Decimal('0')
                
                mov.costo_unitario_calculado = float(costo_promedio_salida)
                mov.costo_total_calculado = float(costo_total_salida)
            
            # Calcular saldo actual
            saldo_cantidad = sum(lote['cantidad'] for lote in lotes)
            saldo_valor = sum(lote['cantidad'] * lote['costo_unitario'] for lote in lotes)
            
            mov.saldo_cantidad_calculado = float(saldo_cantidad)
            mov.saldo_valor_calculado = float(saldo_valor)
    
    def calcular_ueps(self):
        """Calcula kardex con método UEPS (LIFO)"""
        # Pila de lotes (los últimos en entrar)
        lotes = []
        
        for mov in self.movimientos:
            if mov.cantidad_entrada > 0:
                # Entrada: agregar nuevo lote al final
                lotes.append({
                    'cantidad': Decimal(str(mov.cantidad_entrada)),
                    'costo_unitario': Decimal(str(mov.costo_unitario))
                })
                
                mov.costo_unitario_calculado = float(mov.costo_unitario)
                
            else:
                # Salida: tomar de los últimos lotes
                cantidad_pendiente = Decimal(str(mov.cantidad_salida))
                costo_total_salida = Decimal('0')
                
                while cantidad_pendiente > 0 and lotes:
                    lote = lotes[-1]  # Último lote (LIFO)
                    
                    if lote['cantidad'] <= cantidad_pendiente:
                        # Consumir lote completo
                        costo_total_salida += lote['cantidad'] * lote['costo_unitario']
                        cantidad_pendiente -= lote['cantidad']
                        lotes.pop()
                    else:
                        # Consumir parte del lote
                        costo_total_salida += cantidad_pendiente * lote['costo_unitario']
                        lote['cantidad'] -= cantidad_pendiente
                        cantidad_pendiente = Decimal('0')
                
                if mov.cantidad_salida > 0:
                    costo_promedio_salida = costo_total_salida / Decimal(str(mov.cantidad_salida))
                else:
                    costo_promedio_salida = Decimal('0')
                
                mov.costo_unitario_calculado = float(costo_promedio_salida)
                mov.costo_total_calculado = float(costo_total_salida)
            
            # Calcular saldo actual
            saldo_cantidad = sum(lote['cantidad'] for lote in lotes)
            saldo_valor = sum(lote['cantidad'] * lote['costo_unitario'] for lote in lotes)
            
            mov.saldo_cantidad_calculado = float(saldo_cantidad)
            mov.saldo_valor_calculado = float(saldo_valor)
    
    def mostrar_kardex(self):
        """Muestra el kardex en la tabla"""
        self.tabla.setRowCount(len(self.movimientos))
        
        moneda_simbolo = "S/" if self.cmb_moneda_vista.currentData() == "SOLES" else "$"
        
        for row, mov in enumerate(self.movimientos):
            # Fecha
            self.tabla.setItem(row, 0, QTableWidgetItem(mov.fecha_documento.strftime('%d/%m/%Y')))
            
            # Documento
            doc = f"{mov.tipo_documento.value if mov.tipo_documento else ''} {mov.numero_documento or ''}"
            self.tabla.setItem(row, 1, QTableWidgetItem(doc))
            
            # Detalle
            detalle = mov.tipo.value
            if mov.proveedor_id:
                detalle += f" - {mov.proveedor_id}"
            elif mov.destino_id:
                detalle += f" - {mov.destino_id}"
            self.tabla.setItem(row, 2, QTableWidgetItem(detalle))
            
            # Entrada
            if mov.cantidad_entrada > 0:
                self.tabla.setItem(row, 3, QTableWidgetItem(f"{mov.cantidad_entrada:.2f}"))
                cu = getattr(mov, 'costo_unitario_calculado', mov.costo_unitario)
                self.tabla.setItem(row, 4, QTableWidgetItem(f"{moneda_simbolo} {cu:.2f}"))
                self.tabla.setItem(row, 5, QTableWidgetItem(f"{moneda_simbolo} {mov.cantidad_entrada * cu:.2f}"))
            else:
                self.tabla.setItem(row, 3, QTableWidgetItem(""))
                self.tabla.setItem(row, 4, QTableWidgetItem(""))
                self.tabla.setItem(row, 5, QTableWidgetItem(""))
            
            # Salida
            if mov.cantidad_salida > 0:
                self.tabla.setItem(row, 6, QTableWidgetItem(f"{mov.cantidad_salida:.2f}"))
                cu = getattr(mov, 'costo_unitario_calculado', 0)
                ct = getattr(mov, 'costo_total_calculado', 0)
                self.tabla.setItem(row, 7, QTableWidgetItem(f"{moneda_simbolo} {cu:.2f}"))
                self.tabla.setItem(row, 8, QTableWidgetItem(f"{moneda_simbolo} {ct:.2f}"))
            else:
                self.tabla.setItem(row, 6, QTableWidgetItem(""))
                self.tabla.setItem(row, 7, QTableWidgetItem(""))
                self.tabla.setItem(row, 8, QTableWidgetItem(""))
            
            # Saldo
            saldo_cant = getattr(mov, 'saldo_cantidad_calculado', mov.saldo_cantidad)
            saldo_val = getattr(mov, 'saldo_valor_calculado', mov.saldo_costo_total)
            self.tabla.setItem(row, 9, QTableWidgetItem(f"{saldo_cant:.2f}"))
            self.tabla.setItem(row, 10, QTableWidgetItem(f"{moneda_simbolo} {saldo_val:.2f}"))
        
        # Resumen
        if self.movimientos:
            ultimo = self.movimientos[-1]
            saldo_final_cant = getattr(ultimo, 'saldo_cantidad_calculado', ultimo.saldo_cantidad)
            saldo_final_val = getattr(ultimo, 'saldo_valor_calculado', ultimo.saldo_costo_total)
            
            total_entradas = sum(m.cantidad_entrada for m in self.movimientos)
            total_salidas = sum(m.cantidad_salida for m in self.movimientos)
            
            resumen = f"📊 Total Movimientos: {len(self.movimientos)} | "
            resumen += f"Total Entradas: {total_entradas:.2f} | "
            resumen += f"Total Salidas: {total_salidas:.2f} | "
            resumen += f"<strong>Saldo Final: {saldo_final_cant:.2f} unidades = {moneda_simbolo} {saldo_final_val:.2f}</strong>"
            
            self.lbl_resumen.setText(resumen)
    
    def exportar_excel(self):
        """Exporta el kardex a Excel"""
        if not self.movimientos:
            QMessageBox.warning(self, "Error", "Genere primero el kardex")
            return
        
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Kardex",
            f"kardex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel (*.xlsx)"
        )
        
        if not archivo:
            return
        
        try:
            workbook = xlsxwriter.Workbook(archivo)
            worksheet = workbook.add_worksheet('Kardex')
            
            # Formatos
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1a73e8',
                'font_color': 'white',
                'align': 'center'
            })
            
            number_format = workbook.add_format({'num_format': '#,##0.00'})
            
            # Headers
            headers = ['Fecha', 'Documento', 'Detalle', 
                      'Entrada Cant.', 'Entrada C.U.', 'Entrada Total',
                      'Salida Cant.', 'Salida C.U.', 'Salida Total',
                      'Saldo Cant.', 'Saldo Total']
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Datos
            for row, mov in enumerate(self.movimientos, start=1):
                worksheet.write(row, 0, mov.fecha_documento.strftime('%d/%m/%Y'))
                worksheet.write(row, 1, f"{mov.tipo_documento.value if mov.tipo_documento else ''} {mov.numero_documento or ''}")
                worksheet.write(row, 2, mov.tipo.value)
                
                if mov.cantidad_entrada > 0:
                    worksheet.write(row, 3, mov.cantidad_entrada, number_format)
                    cu = getattr(mov, 'costo_unitario_calculado', mov.costo_unitario)
                    worksheet.write(row, 4, cu, number_format)
                    worksheet.write(row, 5, mov.cantidad_entrada * cu, number_format)
                
                if mov.cantidad_salida > 0:
                    worksheet.write(row, 6, mov.cantidad_salida, number_format)
                    cu = getattr(mov, 'costo_unitario_calculado', 0)
                    ct = getattr(mov, 'costo_total_calculado', 0)
                    worksheet.write(row, 7, cu, number_format)
                    worksheet.write(row, 8, ct, number_format)
                
                saldo_cant = getattr(mov, 'saldo_cantidad_calculado', mov.saldo_cantidad)
                saldo_val = getattr(mov, 'saldo_valor_calculado', mov.saldo_costo_total)
                worksheet.write(row, 9, saldo_cant, number_format)
                worksheet.write(row, 10, saldo_val, number_format)
            
            workbook.close()
            
            QMessageBox.information(self, "Éxito", f"Kardex exportado a:\n{archivo}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{str(e)}")


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    ventana = KardexWindow()
    ventana.resize(1400, 800)
    ventana.show()
    
    sys.exit(app.exec())
