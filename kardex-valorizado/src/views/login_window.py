"""
Pantalla de Login - Sistema Kardex Valorizado
Archivo: src/views/login_window.py
(Con nuevo tema de estilo corporativo)
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QFrame, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
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
        self.setWindowTitle("Kardex Valorizado - Iniciar Sesión")
        self.setFixedSize(450, 650) 
        
        # --- NUEVA HOJA DE ESTILO (QSS) BASADA EN LAS CAPTURAS ---
        self.setStyleSheet("""
            /* --- Base de la Ventana --- */
            /* Usamos objectName para que el fondo gris no afecte los QFrame */
            QWidget#LoginWindow {
                background-color: #EEEEEE; /* Fondo gris claro (como el de TR) */
            }

            /* --- Contenedores (Fondo Blanco) --- */
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 30px;
            }

            /* --- Títulos (Logo) --- */
            QLabel#titulo {
                color: #1a73e8; /* Mantenemos tu azul original para el logo */
                padding: 10px;
                font-size: 24px;
                font-weight: bold;
                font-family: Arial;
            }
            QLabel#subtitulo {
                color: #5f6368;
                padding-bottom: 10px;
                font-size: 11px;
                font-family: Arial;
            }
            
            /* --- Etiquetas (Usuario, Contraseña, Año) --- */
            QLabel {
                color: #003366; /* Azul corporativo oscuro (como el de TR) */
                font-weight: bold;
                font-size: 11px;
                font-family: Arial;
            }

            /* --- Campos de Entrada --- */
            QLineEdit, QComboBox {
                background-color: white;
                border: 1px solid #BDBDBD; /* Borde gris estándar */
                border-radius: 4px;
                padding: 8px;
                color: #333333; /* Texto dentro del campo */
                font-size: 11px;
                font-family: Arial;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #005A9C; /* Borde azul oscuro al seleccionar */
            }
            QLineEdit::placeholder {
                color: #AAAAAA;
            }

            /* --- Estilo de la lista del ComboBox --- */
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #BDBDBD;
                selection-background-color: #005A9C; /* Fondo azul al seleccionar item */
                selection-color: white;
            }

            /* --- Botones --- */
            QPushButton {
                background-color: #E0E0E0; /* Fondo gris claro, como el botón 'Ingresar' de TR */
                color: #003366; /* Texto azul */
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 11px;
                font-family: Arial;
            }
            QPushButton:hover {
                background-color: #E8E8E8; /* Un poco más claro al pasar el mouse */
                border-color: #AAAAAA;
            }
            QPushButton:pressed {
                background-color: #D0D0D0; /* Un poco más oscuro al presionar */
            }
            
            /* Botón por defecto (Aceptar e Ingresar) - lo hacemos un poco más oscuro */
            QPushButton:default {
                background-color: #D5D5D5;
                border: 1px solid #ADADAD;
            }

            /* --- Mensaje de Licencia --- */
            QLabel#lbl_licencia {
                color: #333333;
                font-weight: normal;
                font-size: 9px;
            }
            
            /* --- Footer --- */
            QLabel#footer {
                color: #9aa0a6;
                font-weight: normal;
                font-size: 8px;
            }
        """)
        
        # --- Asignar objectName para que el QSS funcione ---
        self.setObjectName("LoginWindow") 

        # Layout principal
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.addStretch()

        # === LOGO / TÍTULO ===
        logo_frame = QFrame()
        logo_layout = QVBoxLayout(logo_frame)

        titulo = QLabel("📦 KARDEX ")
        titulo.setObjectName("titulo") # <-- objectName añadido
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Se quita el setStyleSheet de aquí

        subtitulo = QLabel("Sistema de Gestión de Inventarios")
        subtitulo.setObjectName("subtitulo") # <-- objectName añadido
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Se quita el setStyleSheet de aquí

        logo_layout.addWidget(titulo)
        logo_layout.addWidget(subtitulo)
        layout.addWidget(logo_frame)

        # === FORMULARIO ===
        self.form_frame = QFrame()
        form_layout = QVBoxLayout(self.form_frame)
        form_layout.setSpacing(15)

        # --- Campos de Usuario y Contraseña ---
        user_label = QLabel("Usuario")
        # Se quita el setFont de aquí (controlado por QSS)
        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("Ingrese su usuario")
        self.txt_usuario.returnPressed.connect(self.verificar_credenciales)

        pass_label = QLabel("Contraseña")
        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Ingrese su contraseña")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.returnPressed.connect(self.verificar_credenciales)

        # Botón para verificar credenciales
        self.btn_verificar = QPushButton("Siguiente")
        self.btn_verificar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_verificar.clicked.connect(self.verificar_credenciales)

        # --- Selector de Año (inicialmente oculto) ---
        self.anio_label = QLabel("Seleccionar Año de Trabajo")
        self.anio_combo = QComboBox()
        self.anio_combo.setPlaceholderText("Cargando años...")
        
        self.btn_aceptar = QPushButton("Aceptar e Ingresar")
        self.btn_aceptar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_aceptar.setDefault(True) # <-- Esto activa el estilo :default
        self.btn_aceptar.clicked.connect(self.finalizar_login)
        self.anio_combo.activated.connect(self.finalizar_login)

        self.anio_label.hide()
        self.anio_combo.hide()
        self.btn_aceptar.hide()

        # Agregar widgets al formulario
        form_layout.addWidget(user_label)
        form_layout.addWidget(self.txt_usuario)
        form_layout.addWidget(pass_label)
        form_layout.addWidget(self.txt_password)
        form_layout.addSpacing(10)
        form_layout.addWidget(self.btn_verificar)
        form_layout.addWidget(self.anio_label)
        form_layout.addWidget(self.anio_combo)
        form_layout.addWidget(self.btn_aceptar)

        layout.addWidget(self.form_frame)

        # === INFO DE LICENCIA ===
        self.lbl_licencia = QLabel()
        self.lbl_licencia.setObjectName("lbl_licencia") # <-- objectName añadido
        self.lbl_licencia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verificar_licencia_startup()
        layout.addWidget(self.lbl_licencia)

        layout.addStretch()

        # Footer
        footer = QLabel("© 2024 Sistema Kardex Valorizado v1.0")
        footer.setObjectName("footer") # <-- objectName añadido
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Se quita el setStyleSheet de aquí
        layout.addWidget(footer)

        self.setLayout(layout)
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

    def mostrar_seleccion_anio(self):
        """Paso 2: Oculta campos de login y muestra el selector de año."""
        self.txt_usuario.setEnabled(False)
        self.txt_password.setEnabled(False)
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