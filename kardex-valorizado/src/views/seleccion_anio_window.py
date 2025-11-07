"""
Ventana de Selección de Año Contable
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox,
                             QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

# Acceso a la base de datos y al contexto
from models.database_model import obtener_session, AnioContable, EstadoAnio
from utils.app_context import app_context

class SeleccionAnioWindow(QDialog):
    """
    Diálogo modal para que el usuario seleccione el año en el que desea trabajar.
    """
    # Señal emitida cuando un año es seleccionado y aceptado
    login_exitoso_con_anio = pyqtSignal(dict)

    def __init__(self, user_info, parent=None):
        super().__init__(parent)
        self.user_info = user_info
        self.anios_disponibles = []
        self.init_ui()
        self.cargar_anios_abiertos()

    def init_ui(self):
        self.setWindowTitle("Seleccionar Año de Trabajo")
        self.setModal(True)
        self.setMinimumSize(350, 150)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Etiqueta de bienvenida
        self.bienvenida_label = QLabel(f"¡Hola, {self.user_info['nombre_completo']}!")
        self.bienvenida_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bienvenida_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        # Etiqueta de instrucción
        self.info_label = QLabel("Por favor, selecciona el año contable para continuar:")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ComboBox para los años
        self.anio_combo = QComboBox()
        self.anio_combo.setPlaceholderText("Cargando años...")

        # Botones
        self.aceptar_button = QPushButton("Aceptar")
        self.aceptar_button.clicked.connect(self.aceptar_seleccion)
        self.aceptar_button.setDefault(True) # Se activa con Enter

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.clicked.connect(self.reject) # Cierra el diálogo

        # Añadir widgets al layout
        self.layout.addWidget(self.bienvenida_label)
        self.layout.addWidget(self.info_label)
        self.layout.addWidget(self.anio_combo)
        self.layout.addWidget(self.aceptar_button)
        self.layout.addWidget(self.cancelar_button)

    def cargar_anios_abiertos(self):
        """
        Consulta la base de datos para obtener los años en estado 'Abierto'.
        """
        session = obtener_session()
        try:
            # Consulta para obtener los años abiertos, ordenados de más reciente a más antiguo
            self.anios_disponibles = session.query(AnioContable).filter(
                AnioContable.estado == EstadoAnio.ABIERTO
            ).order_by(AnioContable.anio.desc()).all()

            # Limpiar el combo y añadir los años
            self.anio_combo.clear()
            if self.anios_disponibles:
                for anio_obj in self.anios_disponibles:
                    self.anio_combo.addItem(str(anio_obj.anio), anio_obj.id)
                self.anio_combo.setPlaceholderText("Selecciona un año")
            else:
                self.anio_combo.setPlaceholderText("No hay años abiertos")
                self.aceptar_button.setEnabled(False)
                QMessageBox.critical(self, "Error Crítico",
                                     "No se encontraron años contables abiertos. "
                                     "Contacta al administrador del sistema.")

        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos",
                                 f"No se pudieron cargar los años: {e}")
            self.aceptar_button.setEnabled(False)
        finally:
            session.close()

    def aceptar_seleccion(self):
        """
        Valida la selección, la guarda en el contexto y cierra el diálogo.
        """
        selected_index = self.anio_combo.currentIndex()
        if selected_index == -1:
            QMessageBox.warning(self, "Selección Vacía", "Debes seleccionar un año para continuar.")
            return

        # Obtener el año (texto) y el id (data)
        anio_seleccionado = int(self.anio_combo.currentText())

        # Guardar en el contexto de la aplicación
        app_context.set_selected_year(anio_seleccionado)
        app_context.set_user_info(self.user_info) # Guardamos también la info del usuario

        # Emitir la señal para notificar a main.py que puede continuar
        self.login_exitoso_con_anio.emit(self.user_info)

        self.accept() # Cierra el diálogo con éxito
