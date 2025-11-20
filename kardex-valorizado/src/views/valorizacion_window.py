"""
Valorización de Inventario - Sistema Kardex Valorizado
Archivo: src/views/valorizacion_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QComboBox, QMessageBox, QHeaderView, QGroupBox,
                              QFileDialog, QCheckBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import xlsxwriter

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, Producto, Empresa, Almacen,
                                   MovimientoStock, Categoria, Moneda)
from utils.widgets import SearchableComboBox


class ValorizacionWindow(QWidget):
    """Ventana de Valorización de Inventario"""
    
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.datos_valorizacion = []
        self.init_ui()
        self.cargar_empresas()
    
    def init_ui(self):
        self.setWindowTitle("Valorización de Inventario")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("💰 Valorización de Inventario")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        
        # === FILTROS ===
        grupo_filtros = QGroupBox("Filtros")
        filtros_layout = QVBoxLayout()
        
        # Fila 1
        fila1 = QHBoxLayout()
        
        fila1.addWidget(QLabel("Empresa:"))
        self.cmb_empresa = SearchableComboBox()
        self.cmb_empresa.setMinimumWidth(300)
        self.cmb_empresa.currentIndexChanged.connect(self.empresa_cambiada)
        fila1.addWidget(self.cmb_empresa, 2)
        
        fila1.addWidget(QLabel("Almacén:"))
        self.cmb_almacen = SearchableComboBox()
        self.cmb_almacen.addItem("Todos los almacenes", None)
        fila1.addWidget(self.cmb_almacen, 1)
        
        fila1.addWidget(QLabel("Categoría:"))
        self.cmb_categoria = SearchableComboBox()
        self.cmb_categoria.addItem("Todas las categorías", None)
        fila1.addWidget(self.cmb_categoria, 1)
        
        filtros_layout.addLayout(fila1)
        
        # Fila 2
        fila2 = QHBoxLayout()
        
        fila2.addWidget(QLabel("Moneda:"))
        self.cmb_moneda_vista = QComboBox()
        self.cmb_moneda_vista.addItem("Soles (S/)", "SOLES")
        self.cmb_moneda_vista.addItem("Dólares ($)", "DOLARES")
        fila2.addWidget(self.cmb_moneda_vista)
        
        self.chk_solo_stock = QCheckBox("Solo productos con stock")
        self.chk_solo_stock.setChecked(True)
        fila2.addWidget(self.chk_solo_stock)
        
        self.chk_agrupar_categoria = QCheckBox("Agrupar por categoría")
        fila2.addWidget(self.chk_agrupar_categoria)
        
        fila2.addStretch()
        
        filtros_layout.addLayout(fila2)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        
        btn_generar = QPushButton("🔍 Generar Reporte")
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
        btn_generar.clicked.connect(self.generar_valorizacion)
        
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
        
        # === RESUMEN ===
        self.lbl_resumen = QLabel()
        self.lbl_resumen.setStyleSheet("""
            background-color: #e8f0fe;
            padding: 15px;
            border-radius: 5px;
            color: #1a73e8;
            font-weight: bold;
            font-size: 14px;
        """)
        layout.addWidget(self.lbl_resumen)
        
        # === TABLA ===
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "Código", "Producto", "Categoría", "Unidad", 
            "Cantidad", "Costo Unit.", "Valor Total"
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
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        self.tabla.setAlternatingRowColors(True)
        
        layout.addWidget(self.tabla)
        
        # Totales por categoría
        self.lbl_totales = QLabel()
        self.lbl_totales.setStyleSheet("""
            background-color: #f1f3f4;
            padding: 15px;
            border-radius: 5px;
            font-size: 12px;
        """)
        layout.addWidget(self.lbl_totales)
        
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
        
        # Cargar almacenes
        self.cmb_almacen.clear()
        self.cmb_almacen.addItem("Todos los almacenes", None)
        
        almacenes = self.session.query(Almacen).filter_by(
            empresa_id=empresa_id,
            activo=True
        ).all()
        
        for alm in almacenes:
            self.cmb_almacen.addItem(alm.nombre, alm.id)
        
        # Cargar categorías
        self.cmb_categoria.clear()
        self.cmb_categoria.addItem("Todas las categorías", None)
        
        categorias = self.session.query(Categoria).filter_by(activo=True).all()
        for cat in categorias:
            self.cmb_categoria.addItem(cat.nombre, cat.id)
    
    def generar_valorizacion(self):
        """Genera la valorización de inventario"""
        empresa_id = self.cmb_empresa.currentData()
        
        if not empresa_id:
            QMessageBox.warning(self, "Error", "Seleccione una empresa")
            return
        
        almacen_id = self.cmb_almacen.currentData()
        categoria_id = self.cmb_categoria.currentData()
        solo_stock = self.chk_solo_stock.isChecked()
        
        # Obtener todos los productos
        query_productos = self.session.query(Producto).filter_by(activo=True)
        
        if categoria_id:
            query_productos = query_productos.filter_by(categoria_id=categoria_id)
        
        productos = query_productos.order_by(Producto.nombre).all()
        
        self.datos_valorizacion = []
        
        for producto in productos:
            # Obtener último movimiento por almacén
            query_mov = self.session.query(MovimientoStock).filter_by(
                empresa_id=empresa_id,
                producto_id=producto.id
            )
            
            if almacen_id:
                query_mov = query_mov.filter_by(almacen_id=almacen_id)
            
            # Obtener últimos movimientos por almacén
            if almacen_id:
                ultimo_mov = query_mov.order_by(MovimientoStock.id.desc()).first()
                
                if ultimo_mov and ultimo_mov.saldo_cantidad > 0:
                    costo_unitario = ultimo_mov.saldo_costo_total / ultimo_mov.saldo_cantidad if ultimo_mov.saldo_cantidad > 0 else 0
                    
                    self.datos_valorizacion.append({
                        'codigo': producto.codigo,
                        'nombre': producto.nombre,
                        'categoria': producto.categoria.nombre,
                        'unidad': producto.unidad_medida,
                        'cantidad': ultimo_mov.saldo_cantidad,
                        'costo_unitario': costo_unitario,
                        'valor_total': ultimo_mov.saldo_costo_total,
                        'almacen': ultimo_mov.almacen.nombre
                    })
            else:
                # Sumar todos los almacenes
                movimientos = query_mov.order_by(MovimientoStock.almacen_id, MovimientoStock.id.desc()).all()
                
                # Obtener último movimiento por almacén
                almacenes_vistos = set()
                cantidad_total = Decimal('0')
                valor_total = Decimal('0')
                
                for mov in movimientos:
                    if mov.almacen_id not in almacenes_vistos:
                        almacenes_vistos.add(mov.almacen_id)
                        cantidad_total += Decimal(str(mov.saldo_cantidad))
                        valor_total += Decimal(str(mov.saldo_costo_total))
                
                if cantidad_total > 0:
                    costo_unitario = valor_total / cantidad_total
                    
                    self.datos_valorizacion.append({
                        'codigo': producto.codigo,
                        'nombre': producto.nombre,
                        'categoria': producto.categoria.nombre,
                        'unidad': producto.unidad_medida,
                        'cantidad': float(cantidad_total),
                        'costo_unitario': float(costo_unitario),
                        'valor_total': float(valor_total),
                        'almacen': 'TODOS'
                    })
        
        # Filtrar solo con stock si está marcado
        if solo_stock:
            self.datos_valorizacion = [d for d in self.datos_valorizacion if d['cantidad'] > 0]
        
        if not self.datos_valorizacion:
            QMessageBox.information(self, "Sin datos", "No hay productos con stock para los filtros seleccionados")
            self.tabla.setRowCount(0)
            self.lbl_resumen.setText("")
            self.lbl_totales.setText("")
            return
        
        # Ordenar por categoría si está marcado
        if self.chk_agrupar_categoria.isChecked():
            self.datos_valorizacion.sort(key=lambda x: (x['categoria'], x['nombre']))
        else:
            self.datos_valorizacion.sort(key=lambda x: x['nombre'])
        
        # Mostrar en tabla
        self.mostrar_valorizacion()
    
    def mostrar_valorizacion(self):
        """Muestra la valorización en la tabla"""
        self.tabla.setRowCount(len(self.datos_valorizacion))
        
        moneda_simbolo = "S/" if self.cmb_moneda_vista.currentData() == "SOLES" else "$"
        
        total_cantidad = 0
        total_valor = Decimal('0')
        totales_categoria = {}
        
        categoria_anterior = None
        
        for row, dato in enumerate(self.datos_valorizacion):
            # Si está agrupado por categoría, mostrar separador
            if self.chk_agrupar_categoria.isChecked() and dato['categoria'] != categoria_anterior:
                if categoria_anterior is not None:
                    # Agregar fila de separación
                    pass
                categoria_anterior = dato['categoria']
            
            # Código
            item_codigo = QTableWidgetItem(dato['codigo'])
            self.tabla.setItem(row, 0, item_codigo)
            
            # Nombre
            self.tabla.setItem(row, 1, QTableWidgetItem(dato['nombre']))
            
            # Categoría
            item_cat = QTableWidgetItem(dato['categoria'])
            if self.chk_agrupar_categoria.isChecked():
                item_cat.setBackground(QColor("#e8f0fe"))
            self.tabla.setItem(row, 2, item_cat)
            
            # Unidad
            self.tabla.setItem(row, 3, QTableWidgetItem(dato['unidad']))
            
            # Cantidad
            item_cant = QTableWidgetItem(f"{dato['cantidad']:,.2f}")
            item_cant.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 4, item_cant)
            
            # Costo Unitario
            item_cu = QTableWidgetItem(f"{moneda_simbolo} {dato['costo_unitario']:,.2f}")
            item_cu.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 5, item_cu)
            
            # Valor Total
            item_vt = QTableWidgetItem(f"{moneda_simbolo} {dato['valor_total']:,.2f}")
            item_vt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_vt.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.tabla.setItem(row, 6, item_vt)
            
            # Acumular totales
            total_cantidad += dato['cantidad']
            total_valor += Decimal(str(dato['valor_total']))
            
            # Totales por categoría
            if dato['categoria'] not in totales_categoria:
                totales_categoria[dato['categoria']] = Decimal('0')
            totales_categoria[dato['categoria']] += Decimal(str(dato['valor_total']))
        
        # Mostrar resumen general
        empresa = self.session.query(Empresa).get(self.cmb_empresa.currentData())
        almacen_texto = self.cmb_almacen.currentText() if self.cmb_almacen.currentData() else "TODOS"
        
        resumen = f"📊 Empresa: {empresa.razon_social} | "
        resumen += f"Almacén: {almacen_texto} | "
        resumen += f"Total Productos: {len(self.datos_valorizacion)} | "
        resumen += f"<strong>VALOR TOTAL INVENTARIO: {moneda_simbolo} {total_valor:,.2f}</strong>"
        
        self.lbl_resumen.setText(resumen)
        
        # Mostrar totales por categoría
        if totales_categoria:
            texto_totales = "<strong>Totales por Categoría:</strong><br/>"
            for cat, valor in sorted(totales_categoria.items()):
                porcentaje = (valor / total_valor * 100) if total_valor > 0 else 0
                texto_totales += f"• {cat}: {moneda_simbolo} {valor:,.2f} ({porcentaje:.1f}%)<br/>"
            
            self.lbl_totales.setText(texto_totales)
    
    def exportar_excel(self):
        """Exporta la valorización a Excel"""
        if not self.datos_valorizacion:
            QMessageBox.warning(self, "Error", "Genere primero el reporte")
            return
        
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Valorización",
            f"valorizacion_inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel (*.xlsx)"
        )
        
        if not archivo:
            return
        
        try:
            workbook = xlsxwriter.Workbook(archivo)
            worksheet = workbook.add_worksheet('Valorización')
            
            # Formatos
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1a73e8',
                'font_color': 'white',
                'align': 'center',
                'border': 1
            })
            
            money_format = workbook.add_format({
                'num_format': '#,##0.00',
                'align': 'right'
            })
            
            number_format = workbook.add_format({
                'num_format': '#,##0.00',
                'align': 'right'
            })
            
            total_format = workbook.add_format({
                'bold': True,
                'bg_color': '#e8f0fe',
                'num_format': '#,##0.00',
                'align': 'right'
            })
            
            # Título
            empresa = self.session.query(Empresa).get(self.cmb_empresa.currentData())
            worksheet.merge_range('A1:G1', f'VALORIZACIÓN DE INVENTARIO - {empresa.razon_social}', header_format)
            worksheet.write('A2', f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            # Headers
            headers = ['Código', 'Producto', 'Categoría', 'Unidad', 'Cantidad', 'Costo Unit.', 'Valor Total']
            
            for col, header in enumerate(headers):
                worksheet.write(3, col, header, header_format)
            
            # Datos
            total_valor = 0
            
            for row, dato in enumerate(self.datos_valorizacion, start=4):
                worksheet.write(row, 0, dato['codigo'])
                worksheet.write(row, 1, dato['nombre'])
                worksheet.write(row, 2, dato['categoria'])
                worksheet.write(row, 3, dato['unidad'])
                worksheet.write(row, 4, dato['cantidad'], number_format)
                worksheet.write(row, 5, dato['costo_unitario'], money_format)
                worksheet.write(row, 6, dato['valor_total'], money_format)
                
                total_valor += dato['valor_total']
            
            # Total
            ultima_fila = len(self.datos_valorizacion) + 4
            worksheet.write(ultima_fila, 5, 'TOTAL:', header_format)
            worksheet.write(ultima_fila, 6, total_valor, total_format)
            
            # Ajustar anchos
            worksheet.set_column('A:A', 20)
            worksheet.set_column('B:B', 40)
            worksheet.set_column('C:C', 20)
            worksheet.set_column('D:D', 10)
            worksheet.set_column('E:F', 15)
            worksheet.set_column('G:G', 18)
            
            workbook.close()
            
            QMessageBox.information(self, "Éxito", f"Reporte exportado a:\n{archivo}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{str(e)}")


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    ventana = ValorizacionWindow()
    ventana.resize(1400, 800)
    ventana.show()
    
    sys.exit(app.exec())
