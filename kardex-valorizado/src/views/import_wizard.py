from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
                             QComboBox, QMessageBox, QProgressBar)
from services.import_service import ImportService
import pandas as pd

class ImportWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = ImportService()
        self.df = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Asistente de Importación Masiva")
        self.resize(800, 600)
        layout = QVBoxLayout(self)

        # Paso 1: Selección
        layout.addWidget(QLabel("1. Seleccione el tipo de datos y el archivo:"))
        
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems(["Productos", "Clientes", "Proveedores", "Tipo de Cambio", "Compras", "Ventas"])
        layout.addWidget(self.cmb_tipo)

        btn_file = QPushButton("Seleccionar Archivo (Excel/CSV)")
        btn_file.clicked.connect(self.seleccionar_archivo)
        layout.addWidget(btn_file)
        
        btn_plantilla = QPushButton("Descargar Plantilla")
        btn_plantilla.clicked.connect(self.descargar_plantilla)
        layout.addWidget(btn_plantilla)

        self.lbl_archivo = QLabel("Ningún archivo seleccionado")
        layout.addWidget(self.lbl_archivo)

        # Paso 2: Previsualización
        layout.addWidget(QLabel("2. Previsualización (Primeras 50 filas):"))
        self.tabla = QTableWidget()
        layout.addWidget(self.tabla)

        # Paso 3: Importar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_importar = QPushButton("Importar Datos")
        btn_importar.setStyleSheet("background-color: #1a73e8; color: white; font-weight: bold; padding: 10px;")
        btn_importar.clicked.connect(self.ejecutar_importacion)
        layout.addWidget(btn_importar)

    def seleccionar_archivo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo", "", "Excel/CSV (*.xlsx *.xls *.csv)")
        if path:
            self.lbl_archivo.setText(path)
            self.cargar_previsualizacion(path)

    def cargar_previsualizacion(self, path):
        try:
            self.df = self.service._leer_archivo(path)
            if self.df is not None:
                # Mostrar en tabla
                self.tabla.setColumnCount(len(self.df.columns))
                self.tabla.setHorizontalHeaderLabels(self.df.columns.astype(str))
                
                preview_data = self.df.head(50)
                self.tabla.setRowCount(len(preview_data))
                
                for r, row in preview_data.iterrows():
                    for c, val in enumerate(row):
                        self.tabla.setItem(r, c, QTableWidgetItem(str(val)))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def ejecutar_importacion(self):
        if self.df is None:
            QMessageBox.warning(self, "Error", "Seleccione un archivo válido primero.")
            return

        tipo = self.cmb_tipo.currentText()
        path = self.lbl_archivo.text()

        self.progress.setVisible(True)
        self.progress.setRange(0, 0) # Indeterminado

        if tipo == "Productos":
            exito, msg, errores = self.service.importar_productos(path)
            
            self.progress.setVisible(False)
            if exito:
                detalles = "\n".join(errores[:10])
                if len(errores) > 10: detalles += "\n..."
                QMessageBox.information(self, "Resultado", f"{msg}\n\nErrores:\n{detalles}")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)

        elif tipo == "Clientes":
            exito, msg, errores = self.service.importar_clientes(path)
            
            self.progress.setVisible(False)
            if exito:
                detalles = "\n".join(errores[:10])
                if len(errores) > 10: detalles += "\n..."
                QMessageBox.information(self, "Resultado", f"{msg}\n\nErrores:\n{detalles}")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)

        elif tipo == "Proveedores":
            exito, msg, errores = self.service.importar_proveedores(path)
            
            self.progress.setVisible(False)
            if exito:
                detalles = "\n".join(errores[:10])
                if len(errores) > 10: detalles += "\n..."
                QMessageBox.information(self, "Resultado", f"{msg}\n\nErrores:\n{detalles}")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)

        elif tipo == "Tipo de Cambio":
            exito, msg, errores = self.service.importar_tipo_cambio(path)
            self.progress.setVisible(False)
            if exito:
                QMessageBox.information(self, "Resultado", f"{msg}")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)

        elif tipo == "Compras":
            exito, msg, errores = self.service.importar_compras(path)
            self.progress.setVisible(False)
            if exito:
                detalles = "\n".join(errores[:10])
                if len(errores) > 10: detalles += "\n..."
                QMessageBox.information(self, "Resultado", f"{msg}\n\nErrores:\n{detalles}")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)

        elif tipo == "Ventas":
             QMessageBox.information(self, "Info", "Importación de Ventas en desarrollo.")
             self.progress.setVisible(False)

        else:
            QMessageBox.information(self, "Info", "Este tipo de importación aún no está implementado.")
            self.progress.setVisible(False)
            self.progress.setVisible(False)

    def descargar_plantilla(self):
        tipo = self.cmb_tipo.currentText()
        if "No impl" in tipo:
            QMessageBox.warning(self, "Aviso", "No hay plantilla disponible para este tipo.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Plantilla", f"plantilla_{tipo.lower()}.xlsx", "Excel (*.xlsx);;CSV (*.csv)")
        if path:
            success, msg = self.service.generar_plantilla(tipo, path)
            if success:
                QMessageBox.information(self, "Éxito", f"Plantilla guardada en:\n{path}")
            else:
                QMessageBox.critical(self, "Error", msg)
