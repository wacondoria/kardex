import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
import os
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.database_model import Producto, MovimientoStock, Venta, Compra, Proveedor, Cliente

class ReportService:
    def __init__(self, session: Session):
        self.session = session
        self.styles = getSampleStyleSheet()
        self.title_style = self.styles['Heading1']
        self.normal_style = self.styles['Normal']

    def _get_output_path(self, filename, folder="exports"):
        if not os.path.exists(folder):
            os.makedirs(folder)
        return os.path.join(folder, filename)

    def generar_reporte_inventario(self, formato='pdf'):
        """Genera un reporte de inventario valorizado."""
        
        # 1. Obtener datos
        query = self.session.query(
            Producto.codigo,
            Producto.nombre,
            Producto.unidad_medida,
            # Aquí deberíamos calcular el stock real y costo promedio
            # Por simplicidad para el reporte, usaremos una subquery o lógica simplificada
            # En un caso real, esto vendría de una vista materializada o cálculo complejo
        ).filter(Producto.activo == True).all()

        # Simulamos datos de stock para el ejemplo (en prod usar KardexManager)
        data = []
        for prod in query:
            # Esto es lento, optimizar en producción
            entradas = self.session.query(func.sum(MovimientoStock.cantidad_entrada)).filter_by(producto_id=prod.codigo).scalar() or 0
            salidas = self.session.query(func.sum(MovimientoStock.cantidad_salida)).filter_by(producto_id=prod.codigo).scalar() or 0
            stock = entradas - salidas
            
            # Costo promedio (simplificado)
            costo = 0.0 # Implementar lógica real
            total = stock * costo
            
            data.append({
                "Código": prod.codigo,
                "Producto": prod.nombre,
                "Unidad": prod.unidad_medida,
                "Stock": stock,
                "Costo Unit.": costo,
                "Total Valorizado": total
            })

        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inventario_valorizado_{timestamp}"

        if formato == 'excel':
            path = self._get_output_path(f"{filename}.xlsx")
            df.to_excel(path, index=False, engine='xlsxwriter')
            return path
        else:
            path = self._get_output_path(f"{filename}.pdf")
            self._crear_pdf(path, "Inventario Valorizado", df)
            return path

    def generar_reporte_ventas(self, fecha_inicio, fecha_fin, formato='pdf'):
        """Genera reporte de ventas por periodo."""
        ventas = self.session.query(Venta).filter(
            Venta.fecha >= fecha_inicio,
            Venta.fecha <= fecha_fin
        ).all()

        data = []
        for v in ventas:
            data.append({
                "Fecha": v.fecha,
                "Documento": f"{v.tipo_documento.value} {v.numero_documento}",
                "Cliente": v.cliente.razon_social if v.cliente else "S/N",
                "Moneda": v.moneda.value,
                "Total": v.total
            })
        
        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reporte_ventas_{timestamp}"

        if formato == 'excel':
            path = self._get_output_path(f"{filename}.xlsx")
            df.to_excel(path, index=False, engine='xlsxwriter')
            return path
        else:
            path = self._get_output_path(f"{filename}.pdf")
            self._crear_pdf(path, f"Reporte de Ventas ({fecha_inicio} - {fecha_fin})", df)
            return path

    def _crear_pdf(self, path, titulo, df):
        doc = SimpleDocTemplate(path, pagesize=landscape(A4))
        elements = []

        # Título
        elements.append(Paragraph(titulo, self.title_style))
        elements.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", self.normal_style))
        elements.append(Spacer(1, 20))

        # Tabla
        if not df.empty:
            lista_datos = [df.columns.values.tolist()] + df.values.tolist()
            t = Table(lista_datos)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("No hay datos para mostrar.", self.normal_style))

        doc.build(elements)
