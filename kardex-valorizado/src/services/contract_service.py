from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from models.database_model import Alquiler
from datetime import date
import os

class ContractService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.style_normal = self.styles["Normal"]
        self.style_title = self.styles["Title"]
        self.style_heading = self.styles["Heading2"]

    def generate_contract(self, alquiler: Alquiler, output_path: str):
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # 1. Header / Title
        story.append(Paragraph("CONTRATO DE ALQUILER DE EQUIPOS", self.style_title))
        story.append(Spacer(1, 1*cm))
        
        # 2. Contract Info
        data_contrato = [
            [Paragraph(f"<b>Nro. Contrato:</b> {alquiler.id:06d}", self.style_normal),
             Paragraph(f"<b>Fecha:</b> {date.today().strftime('%d/%m/%Y')}", self.style_normal)]
        ]
        t_info = Table(data_contrato, colWidths=[10*cm, 6*cm])
        t_info.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_info)
        story.append(Spacer(1, 0.5*cm))
        
        # 3. Parties
        cliente_nombre = alquiler.cliente.razon_social_o_nombre
        cliente_doc = alquiler.cliente.numero_documento
        cliente_dir = alquiler.cliente.direccion or "S/D"
        
        texto_partes = f"""
        <b>ARRENDADOR:</b> KARDEX VALORIZADO S.A.C.<br/>
        <b>ARRENDATARIO:</b> {cliente_nombre}, identificado con RUC/DNI {cliente_doc}, con domicilio en {cliente_dir}.
        """
        story.append(Paragraph(texto_partes, self.style_normal))
        story.append(Spacer(1, 0.5*cm))
        
        # 4. Rental Details
        fecha_inicio = alquiler.fecha_inicio.strftime('%d/%m/%Y')
        fecha_fin = alquiler.fecha_fin_estimada.strftime('%d/%m/%Y') if alquiler.fecha_fin_estimada else "Indefinido"
        obra = alquiler.ubicacion_obra or "No especificada"
        
        texto_detalles = f"""
        <b>Ubicación de Obra:</b> {obra}<br/>
        <b>Periodo de Alquiler:</b> Del {fecha_inicio} al {fecha_fin}
        """
        story.append(Paragraph(texto_detalles, self.style_normal))
        story.append(Spacer(1, 0.5*cm))
        
        # 5. Equipment List
        story.append(Paragraph("EQUIPOS ALQUILADOS", self.style_heading))
        story.append(Spacer(1, 0.2*cm))
        
        data_equipos = [["Código", "Descripción", "Cant.", "Tarifa Unit.", "Total"]]
        total_alquiler = 0.0
        
        for det in alquiler.detalles:
            subtotal = det.total # Assuming total is calculated and stored
            # If total is 0 or None, calc on fly
            if not subtotal:
                subtotal = det.precio_unitario * (det.cantidad if hasattr(det, 'cantidad') else 1)
                
            data_equipos.append([
                det.equipo.codigo,
                Paragraph(det.equipo.nombre, self.style_normal),
                "1", # Assuming 1 per line for serialized
                f"S/ {det.precio_unitario:.2f}",
                f"S/ {subtotal:.2f}"
            ])
            total_alquiler += subtotal
            
        t_equipos = Table(data_equipos, colWidths=[2.5*cm, 7*cm, 1.5*cm, 2.5*cm, 2.5*cm])
        t_equipos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'), # Description left align
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        story.append(t_equipos)
        story.append(Spacer(1, 1*cm))
        
        # 6. Terms
        story.append(Paragraph("TÉRMINOS Y CONDICIONES", self.style_heading))
        terms = """
        1. El ARRENDATARIO se compromete a cuidar y conservar los equipos en buen estado.<br/>
        2. El ARRENDATARIO asume la responsabilidad por pérdida o daños causados por mal uso.<br/>
        3. El pago se realizará según las condiciones pactadas en la cotización.<br/>
        4. La devolución de los equipos deberá realizarse en las instalaciones del ARRENDADOR salvo acuerdo contrario.
        """
        story.append(Paragraph(terms, self.style_normal))
        story.append(Spacer(1, 2*cm))
        
        # 7. Signatures
        data_firmas = [
            ["__________________________", "__________________________"],
            ["POR EL ARRENDADOR", "POR EL ARRENDATARIO"],
            ["KARDEX VALORIZADO S.A.C.", f"{cliente_nombre}"]
        ]
        t_firmas = Table(data_firmas, colWidths=[8*cm, 8*cm])
        t_firmas.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_firmas)
        
        doc.build(story)
        return True
