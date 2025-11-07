"""
Pantalla de Login - Sistema Kardex Valorizado
Archivo: src/views/login_window.py
(Con nuevo tema de estilo corporativo)
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QFrame, QComboBox,
                             QGridLayout, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon
from werkzeug.security import check_password_hash
from datetime import datetime, date
import sys
from pathlib import Path

# Agregar src al path si no está
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, Usuario, Licencia,
                                   AnioContable, EstadoAnio)
from utils.app_context import app_context

# --- NO SE USA EL TEMA OSCURO ---
# from utils.theme import DARK_THEME_QSS 


class LoginWindow(QWidget):
    """
    Ventana de Login del sistema.
    Autentica al usuario y permite seleccionar el año fiscal en una sola vista.
    """

    login_exitoso = pyqtSignal(dict)  # Emite info del usuario autenticado

    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.user_info = None  # Almacenará la info del usuario validado
        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("KARDEX v1.4.4 - Modulo De Inventarios valorizado")
        self.setFixedSize(400, 250)

        self.setStyleSheet("""
            QWidget#LoginWindow { background-color: #E0E0E0; }
            QLabel { color: #003366; font-weight: bold; font-size: 11px; font-family: Arial; }
            QLineEdit {
                border: 1px solid #8C8C8C;
                background-color: #FFFFFF;
                padding: 4px;
                border-radius: 3px;
                box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.5);
            }
            QPushButton {
                background-color: #F0F0F0; border: 1px solid #8C8C8C;
                padding: 4px; text-align: right;
            }
        """)
        self.setObjectName("LoginWindow")

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.addStretch(1)

        # Logo
        logo_label = QLabel()
        pixmap = QPixmap("src/resources/logo.png")
        logo_label.setPixmap(pixmap.scaled(300, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(logo_label)
        main_layout.addSpacing(20)

        # Formulario
        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(15)

        user_label = QLabel("Usuario:")
        self.txt_usuario = QLineEdit()

        self.pass_label = QLabel("Contraseña:")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)

        self.btn_verificar = QPushButton("Ingresar")
        self.btn_verificar.setIcon(QIcon("src/resources/login_icon.png"))
        self.btn_verificar.setIconSize(QSize(16, 16))
        self.btn_verificar.setMinimumSize(70, 28)

        self.anio_label = QLabel("Seleccionar Año:")
        self.anio_combo = QComboBox()
        self.btn_aceptar = QPushButton("✅ Aceptar")
        self.btn_aceptar.setMinimumSize(70, 28)

        self.anio_label.hide()
        self.anio_combo.hide()
        self.btn_aceptar.hide()

        form_layout.addWidget(user_label, 0, 0)
        form_layout.addWidget(self.txt_usuario, 0, 1, 1, 2)

        form_layout.addWidget(self.pass_label, 1, 0)
        form_layout.addWidget(self.txt_password, 1, 1)
        form_layout.addWidget(self.btn_verificar, 1, 2)

        form_layout.addWidget(self.anio_label, 2, 0)
        form_layout.addWidget(self.anio_combo, 2, 1)
        form_layout.addWidget(self.btn_aceptar, 2, 2)

        main_layout.addLayout(form_layout)
        main_layout.addStretch(2)

        # === INFO DE LICENCIA ===
        self.lbl_licencia = QLabel()
        self.lbl_licencia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_licencia.setStyleSheet("font-size: 9px; font-weight: normal; color: #555;")
        self.verificar_licencia_startup()
        main_layout.addWidget(self.lbl_licencia)

        # Conectar señales
        self.txt_usuario.returnPressed.connect(self.txt_password.setFocus)
        self.txt_password.returnPressed.connect(self.btn_verificar.click)
        self.btn_verificar.clicked.connect(self.verificar_credenciales)
        self.btn_aceptar.clicked.connect(self.finalizar_login)
        self.anio_combo.activated.connect(self.finalizar_login)

        self.txt_usuario.setFocus()
    
    # ... (El resto de tus funciones: verificar_credenciales, mostrar_seleccion_anio, etc.) ...
    # ... (No necesitas cambiar ninguna de las funciones lógicas) ...
    
    def verificar_credenciales(self):
        """Paso 1: Valida usuario y contraseña."""
        usuario = self.txt_usuario.text().strip()
        password = self.txt_password.text()

        if not usuario or not password:
            QMessageBox.warning(self, "Campos vacíos", "Por favor ingrese usuario y contraseña.")
            return

        try:
            user = self.session.query(Usuario).filter_by(username=usuario, activo=True).first()

            if not user or not check_password_hash(user.password_hash, password):
                QMessageBox.critical(self, "Error de autenticación", "Usuario o contraseña incorrecta.")
                self.txt_password.clear()
                return

            user.ultimo_acceso = datetime.now()
            self.session.commit()

            self.user_info = {
                'id': user.id, 'username': user.username, 'nombre_completo': user.nombre_completo,
                'rol': user.rol.value, 'email': user.email,
                'licencia_vencida': self.verificar_licencia_activa()
            }

            if self.user_info['licencia_vencida']:
                QMessageBox.warning(self, "Licencia Vencida",
                                    f"Bienvenido {user.nombre_completo}.\n\n"
                                    "La licencia ha vencido. Solo podrás CONSULTAR información.")

            self.mostrar_seleccion_anio()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar login:\n{str(e)}")

    def verificar_licencia_startup(self):
        """Verifica el estado de la licencia al iniciar."""
        try:
            licencia = self.session.query(Licencia).filter_by(activa=True).first()
            if not licencia:
                self.lbl_licencia.setText("⚠️ No hay licencia instalada - Modo demostración")
                return

            hoy = date.today()
            dias_restantes = (licencia.fecha_vencimiento - hoy).days

            if dias_restantes < 0:
                self.lbl_licencia.setText(f"❌ Licencia VENCIDA (hace {abs(dias_restantes)} días)")
            elif dias_restantes <= 30:
                self.lbl_licencia.setText(f"⚠️ Licencia vence en {dias_restantes} días")
            else:
                self.lbl_licencia.setText(f"✓ Licencia vigente ({dias_restantes} días restantes)")

        except Exception:
            self.lbl_licencia.setText("⚠️ Error al verificar licencia")

    def mostrar_seleccion_anio(self):
        """Paso 2: Oculta campos de login y muestra el selector de año."""
        self.txt_usuario.setEnabled(False)
        self.pass_label.hide()
        self.txt_password.hide()
        self.btn_verificar.hide()

        self.anio_label.show()
        self.anio_combo.show()
        self.btn_aceptar.show()

        self.cargar_anios_abiertos()
        self.anio_combo.setFocus()

    def cargar_anios_abiertos(self):
        """Consulta y carga los años abiertos en el ComboBox."""
        try:
            anios = self.session.query(AnioContable).filter(
                AnioContable.estado == EstadoAnio.ABIERTO
            ).order_by(AnioContable.anio.desc()).all()

            if not anios:
                self.anio_combo.setPlaceholderText("No hay años abiertos")
                self.btn_aceptar.setEnabled(False)
                QMessageBox.critical(self, "Error Crítico",
                                     "No se encontraron años contables abiertos. Contacta al administrador.")
                return

            for anio_obj in anios:
                self.anio_combo.addItem(str(anio_obj.anio), anio_obj.id)

        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"No se pudieron cargar los años: {e}")
            self.btn_aceptar.setEnabled(False)

    def finalizar_login(self):
        """Paso 3: Guarda el año seleccionado, emite la señal y cierra."""
        if self.anio_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Selección Vacía", "Debes seleccionar un año para continuar.")
            return

        anio_seleccionado = int(self.anio_combo.currentText())

        app_context.set_selected_year(anio_seleccionado)
        app_context.set_user_info(self.user_info)

        self.login_exitoso.emit(self.user_info)
        self.close()

    def verificar_licencia_activa(self):
        """Verifica si la licencia está vencida."""
        try:
            licencia = self.session.query(Licencia).filter_by(activa=True).first()
            if not licencia: return True
            return (licencia.fecha_vencimiento - date.today()).days < 0
        except:
            return True

    def closeEvent(self, event):
        """Al cerrar la ventana."""
        self.session.close()
        event.accept()


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion') # Fusion sigue siendo una buena base

    login = LoginWindow()
    login.show()

    sys.exit(app.exec())