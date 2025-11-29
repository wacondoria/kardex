"""
Dashboard Widget - Sistema Kardex Valorizado
Archivo: src/views/dashboard_view.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QListWidget, QListWidgetItem, QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract, case

# Importar matplotlib
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, Venta, Compra, Producto,
                                   OrdenCompra, EstadoOrden)
from utils.app_context import app_context

class KPICard(QFrame):
    """Tarjeta para mostrar un Indicador Clave de Desempeño (KPI)"""
    def __init__(self, title, value, icon_char="📊", color="#1a73e8"):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            KPICard {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid #ddd;
            }}
            QLabel#ValueLabel {{
                color: {color};
                font-size: 24px;
                font-weight: bold;
            }}
            QLabel#TitleLabel {{
                color: #666;
                font-size: 12px;
            }}
        """)

        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        icon_label = QLabel(icon_char)
        icon_label.setFont(QFont("Segoe UI Emoji", 20))
        header_layout.addWidget(icon_label)
        header_layout.addStretch()

        self.value_label = QLabel(value)
        self.value_label.setObjectName("ValueLabel")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addLayout(header_layout)
        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

class DashboardWidget(QWidget):
    """
    Dashboard principal con KPIs, gráficos y alertas.
    """
    def __init__(self):
        super().__init__()
    def __init__(self):
        super().__init__()
        # self.session removido para evitar mantener conexiones abiertas
        self.init_ui()
        self.cargar_datos()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 1. Encabezado
        header_label = QLabel("📊 Panel de Control")
        header_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #1a73e8;")
        main_layout.addWidget(header_label)

        # 2. Tarjetas KPI
        kpi_layout = QHBoxLayout()

        self.kpi_ventas = KPICard("Ventas del Día", "S/ 0.00", "💰", "#28a745")
        self.kpi_compras = KPICard("Compras del Mes", "S/ 0.00", "🛒", "#dc3545")
        self.kpi_stock = KPICard("Productos Críticos", "0", "⚠️", "#ffc107")

        kpi_layout.addWidget(self.kpi_ventas)
        kpi_layout.addWidget(self.kpi_compras)
        kpi_layout.addWidget(self.kpi_stock)

        main_layout.addLayout(kpi_layout)

        # 3. Gráfico y Alertas (Grid)
        content_grid = QGridLayout()
        content_grid.setColumnStretch(0, 2) # Gráfico más ancho
        content_grid.setColumnStretch(1, 1) # Alertas más angosto

        # --- Gráfico ---
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #ddd;")
        chart_layout = QVBoxLayout(chart_frame)

        chart_title = QLabel("📈 Ventas vs. Compras (Últimos 6 meses)")
        chart_title.setStyleSheet("font-weight: bold; color: #555; font-size: 14px;")
        chart_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(chart_title)

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)

        content_grid.addWidget(chart_frame, 0, 0)

        # --- Alertas / Tareas Pendientes ---
        alerts_frame = QFrame()
        alerts_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #ddd;")
        alerts_layout = QVBoxLayout(alerts_frame)

        alerts_title = QLabel("🔔 Tareas Pendientes")
        alerts_title.setStyleSheet("font-weight: bold; color: #555; font-size: 14px;")
        alerts_layout.addWidget(alerts_title)

        self.list_alerts = QListWidget()
        self.list_alerts.setStyleSheet("border: none;")
        alerts_layout.addWidget(self.list_alerts)

        content_grid.addWidget(alerts_frame, 0, 1)

        main_layout.addLayout(content_grid)

    def cargar_datos(self):
        """Recupera los datos de la BD y actualiza los widgets."""
        session = obtener_session()
        try:
            hoy = date.today()
            anio_actual = hoy.year
            mes_actual = hoy.month

            # --- KPI 1: Ventas del Día ---
            ventas_dia = session.query(func.sum(Venta.total)).filter(
                func.date(Venta.fecha) == hoy
            ).scalar() or 0.0
            self.kpi_ventas.value_label.setText(f"S/ {ventas_dia:,.2f}")

            # --- KPI 2: Compras del Mes ---
            compras_mes = session.query(func.sum(Compra.total)).filter(
                extract('year', Compra.fecha) == anio_actual,
                extract('month', Compra.fecha) == mes_actual
            ).scalar() or 0.0
            self.kpi_compras.value_label.setText(f"S/ {compras_mes:,.2f}")

            # --- KPI 3: Productos Críticos ---
            # Productos activos donde el stock actual sea menor al stock mínimo.
            # Nota: Calcular stock actual es costoso si se hace por Kardex.
            # Si no hay campo 'stock_actual' cacheado en Producto, esto puede ser lento.
            # Asumiremos que no hay campo cacheado y haremos una estimación rápida o
            # usaremos una query optimizada sobre MovimientoStock.
            # Para simplificar y no bloquear el UI, contaremos productos con stock_minimo > 0
            # y trataremos de inferir (o dejaremos en 0 si es muy complejo sin cache).
            #
            # Una alternativa mejor: Usar KardexManager si tiene método optimizado.
            # Si no, una subquery simple de MovimientoStock agrupada.

            # Subquery para saldo por producto
            # SELECT producto_id, SUM(cantidad_entrada - cantidad_salida) as saldo
            # FROM movimientos_stock GROUP BY producto_id

            # Esto puede ser pesado. Limitaremos a productos con stock mínimo definido.
            prods_con_minimo = session.query(Producto).filter(
                Producto.activo == True,
                Producto.stock_minimo > 0
            ).all()

            # Optimización: Consulta masiva de stocks
            # Subquery para obtener el último movimiento de cada producto en cada almacén
            from models.database_model import MovimientoStock
            
            product_ids = [p.id for p in prods_con_minimo]
            
            criticos_count = 0
            if product_ids:
                subquery = (
                    session.query(
                        func.max(MovimientoStock.id).label('max_id')
                    )
                    .filter(MovimientoStock.producto_id.in_(product_ids))
                    .group_by(MovimientoStock.producto_id, MovimientoStock.almacen_id)
                    .subquery()
                )

                # Sumar saldo de todos los almacenes por producto
                stocks_query = (
                    session.query(
                        MovimientoStock.producto_id,
                        func.sum(MovimientoStock.saldo_cantidad)
                    )
                    .join(subquery, MovimientoStock.id == subquery.c.max_id)
                    .group_by(MovimientoStock.producto_id)
                    .all()
                )
                
                stock_map = {pid: (stock or 0) for pid, stock in stocks_query}
                
                criticos_count = 0
                for prod in prods_con_minimo:
                    stock_actual = stock_map.get(prod.id, 0)
                    if stock_actual <= prod.stock_minimo:
                        criticos_count += 1
            
            self.kpi_stock.value_label.setText(str(criticos_count))
            if criticos_count > 0:
                self.kpi_stock.value_label.setStyleSheet("color: #dc3545; font-size: 24px; font-weight: bold;")


            # --- GRÁFICO: Ventas vs Compras (6 meses) ---
            self.actualizar_grafico(hoy, session)

            # --- ALERTAS ---
            self.actualizar_alertas(session)

        except Exception as e:
            print(f"Error cargando dashboard: {e}")
            import traceback
            traceback.print_exc()
        finally:
            session.close()

    def actualizar_grafico(self, fecha_ref, session):
        # Calcular rango de 6 meses
        fechas = []
        ventas_data = []
        compras_data = []

        meses_labels = []

        for i in range(5, -1, -1):
            mes_date = date(fecha_ref.year, fecha_ref.month, 1) - timedelta(days=i*30) # Aprox
            # Ajuste mejor para mes
            # Calcular mes y año
            m = fecha_ref.month - i
            y = fecha_ref.year
            while m <= 0:
                m += 12
                y -= 1

            mes_nombre = date(y, m, 1).strftime("%b")
            meses_labels.append(mes_nombre)

            # Consulta Ventas
            v = session.query(func.sum(Venta.total)).filter(
                extract('year', Venta.fecha) == y,
                extract('month', Venta.fecha) == m
            ).scalar() or 0.0
            ventas_data.append(v)

            # Consulta Compras
            c = session.query(func.sum(Compra.total)).filter(
                extract('year', Compra.fecha) == y,
                extract('month', Compra.fecha) == m
            ).scalar() or 0.0
            compras_data.append(c)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        x = range(len(meses_labels))
        width = 0.35

        ax.bar([i - width/2 for i in x], ventas_data, width, label='Ventas', color='#28a745', alpha=0.7)
        ax.bar([i + width/2 for i in x], compras_data, width, label='Compras', color='#dc3545', alpha=0.7)

        ax.set_xticks(x)
        ax.set_xticklabels(meses_labels)
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        self.canvas.draw()

    def actualizar_alertas(self, session):
        self.list_alerts.clear()

        # 1. Órdenes de Compra Pendientes
        try:
            if OrdenCompra and EstadoOrden:
                pendientes = session.query(OrdenCompra).filter_by(estado=EstadoOrden.PENDIENTE).count()
                if pendientes > 0:
                    item = QListWidgetItem(f"📝 {pendientes} Órdenes de Compra por aprobar")
                    item.setForeground(Qt.GlobalColor.darkRed)
                    self.list_alerts.addItem(item)
        except NameError:
            pass # Si no existe el módulo

        # 2. Licencia próxima a vencer (Simulado o real si tienes acceso)
        # (Usar lógica de LoginWindow si fuera accesible, o duplicarla simple)

        # 3. Mensaje si no hay alertas
        if self.list_alerts.count() == 0:
            item = QListWidgetItem("✅ Todo al día. No hay alertas pendientes.")
            item.setForeground(Qt.GlobalColor.darkGreen)
            self.list_alerts.addItem(item)

    def closeEvent(self, event):
        # self.session.close() # Ya no es necesario
        super().closeEvent(event)
