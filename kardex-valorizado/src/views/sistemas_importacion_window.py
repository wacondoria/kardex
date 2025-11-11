"""
Ventana de Importación y Exportación de Plantillas - Sistema Kardex Valorizado
Archivo: src/views/sistemas_importacion_window.py
"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QMessageBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.import_export_manager import ImportExportManager
from utils.kardex_manager import KardexManager
from utils.app_context import app_context

class SistemasImportacionWindow(QWidget):
    """
    Ventana centralizada para generar plantillas e importar datos masivos.
    """
    def __init__(self):
        super().__init__()
        self.manager = ImportExportManager(parent_widget=self)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Central de Importaciones y Plantillas")
        self.setMinimumSize(600, 400)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Título
        header_layout = QHBoxLayout()
        title_label = QLabel("⚙️ Central de Importaciones")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1a73e8;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Grupo de Selección
        selection_group = QGroupBox("Paso 1: Seleccione el Módulo")
        selection_layout = QFormLayout()

        self.cmb_modulos = QComboBox()
        self.cmb_modulos.addItems(["", "Proveedores", "Productos", "Compras", "Ventas", "Tipo de Cambio"])
        self.cmb_modulos.setPlaceholderText("Seleccione un tipo de dato...")

        selection_layout.addRow(QLabel("Módulo a procesar:"), self.cmb_modulos)
        selection_group.setLayout(selection_layout)
        main_layout.addWidget(selection_group)

        # Grupo de Acciones
        actions_group = QGroupBox("Paso 2: Elija una Acción")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(20)

        self.btn_generar_plantilla = QPushButton("📄 Generar Plantilla")
        self.btn_generar_plantilla.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_generar_plantilla.setStyleSheet("""
            QPushButton {
                background-color: #1D6F42; color: white; padding: 12px 25px;
                border: none; border-radius: 5px;
            }
            QPushButton:hover { background-color: #185C37; }
        """)
        self.btn_generar_plantilla.clicked.connect(self.generar_plantilla)

        self.btn_importar_datos = QPushButton("⬆️ Importar Datos")
        self.btn_importar_datos.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_importar_datos.setStyleSheet("""
            QPushButton {
                background-color: #107C41; color: white; padding: 12px 25px;
                border: none; border-radius: 5px;
            }
            QPushButton:hover { background-color: #0D6534; }
        """)
        self.btn_importar_datos.clicked.connect(self.importar_datos)

        actions_layout.addWidget(self.btn_generar_plantilla)
        actions_layout.addWidget(self.btn_importar_datos)
        actions_group.setLayout(actions_layout)
        main_layout.addWidget(actions_group)

        # Grupo de Mantenimiento
        maintenance_group = QGroupBox("Acciones de Mantenimiento")
        maintenance_layout = QHBoxLayout()

        self.btn_recalcular_saldos = QPushButton("🔄 Actualizar Saldos de Inventario")
        self.btn_recalcular_saldos.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_recalcular_saldos.setStyleSheet("""
            QPushButton {
                background-color: #d93025; color: white; padding: 12px 25px;
                border: none; border-radius: 5px;
            }
            QPushButton:hover { background-color: #a52714; }
        """)
        self.btn_recalcular_saldos.clicked.connect(self.recalcular_saldos)

        maintenance_layout.addWidget(self.btn_recalcular_saldos)
        maintenance_layout.addStretch()
        maintenance_group.setLayout(maintenance_layout)
        main_layout.addWidget(maintenance_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def generar_plantilla(self):
        modulo_seleccionado = self.cmb_modulos.currentText()
        if not modulo_seleccionado:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, seleccione un módulo antes de generar una plantilla.")
            return

        self.manager.generar_plantilla(modulo_seleccionado)

    def importar_datos(self):
        modulo_seleccionado = self.cmb_modulos.currentText()
        if not modulo_seleccionado:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, seleccione un módulo antes de importar datos.")
            return

        self.manager.importar_datos(modulo_seleccionado)

    def recalcular_saldos(self):
        """
        Inicia el proceso de recálculo global de saldos de inventario.
        """
        reply = QMessageBox.warning(
            self,
            "Confirmación Requerida",
            "Este proceso recalculará todos los saldos de inventario desde el inicio.\n"
            "Puede tardar varios minutos y no se puede deshacer.\n\n"
            "¿Está seguro de que desea continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            session = app_context.get_session()
            empresa = app_context.get_empresa()
            if not session or not empresa:
                QMessageBox.critical(self, "Error", "No se ha podido obtener la sesión o la empresa del contexto.")
                return

            kardex_manager = KardexManager(session)
            kardex_manager.recalcular_saldos_globales(empresa.id)

            QMessageBox.information(self, "Proceso Completado", "Los saldos de inventario se han recalculado exitosamente.")

        except Exception as e:
            QMessageBox.critical(self, "Error en el Proceso", f"Ocurrió un error al recalcular los saldos:\n{str(e)}")

# Para pruebas locales
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = SistemasImportacionWindow()
    window.show()
    sys.exit(app.exec())
