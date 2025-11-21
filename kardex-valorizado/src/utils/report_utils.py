# kardex-valorizado/src/utils/report_utils.py

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, PageBreak, Image, Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

from models.database_model import Empresa
from utils.app_context import app_context

class BaseReport:
    def __init__(self, path, title, period, filters=None):
        self.path = path
        self.title = title
        self.period = period
        self.filters = filters if filters else {}
        self.doc = SimpleDocTemplate(self.path, pagesize=A4)
        self.elements = []
        self.styles = getSampleStyleSheet()

        # Obtener datos de la empresa y del contexto
        self.session = app_context.get_session()
        self.empresa = app_context.get_empresa()


    def _header_footer(self, canvas, doc):
        # --- Cabecera ---
        canvas.saveState()

        # Logo
        # La ruta debe ser relativa al script que se ejecuta (main.py)
        logo_path = "kardex-valorizado/src/resources/logo.png"
        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, 40, doc.height + 60, width=80, height=40, mask='auto')

        # Títulos
        canvas.setFont('Helvetica-Bold', 16)
        canvas.drawCentredString(doc.width / 2.0 + 40, doc.height + 90, self.title)

        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(doc.width / 2.0 + 40, doc.height + 75, f"Periodo: {self.period}")

        # Datos de la empresa
        if self.empresa:
            canvas.setFont('Helvetica-Bold', 10)
            canvas.drawString(40, doc.height + 40, self.empresa.razon_social)
            canvas.setFont('Helvetica', 9)
            canvas.drawString(40, doc.height + 28, f"RUC: {self.empresa.ruc}")

        canvas.restoreState()

        # --- Pie de página ---
        canvas.saveState()
        canvas.setFont('Helvetica', 8)

        # Fecha y Hora de Emisión
        emission_time = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
        canvas.drawString(40, 30, f"Generado el: {emission_time}")

        # Moneda
        moneda = self.filters.get("Moneda", "SOLES (S/)") # Valor por defecto
        canvas.drawRightString(doc.width + 30, 30, f"Moneda: {moneda}")

        # Número de página
        page_num_text = f"Página {doc.page}"
        canvas.drawCentredString(doc.width / 2.0 + 40, 20, page_num_text)

        canvas.restoreState()


    def generate_report(self):
        self.doc.build(self.elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
