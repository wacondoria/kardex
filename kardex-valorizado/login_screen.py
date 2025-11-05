"""
Pantalla de Login - Sistema Kardex Valorizado
Archivo: src/views/login_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from werkzeug.security import check_password_hash
from datetime import datetime, date
import sys
from pathlib import Path

# Agregar src al path si no está
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Usuario, Licencia


class LoginWindow(QWidget):
    """
    Ventana de Login del sistema
    Emite señal login_exitoso cuando el usuario se autentica correctamente
    """
    
    login_exitoso = pyqtSignal(dict)  # Emite info del usuario autenticado
    
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("Kardex Valorizado - Iniciar Sesión")
        self.setFixedSize(450, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f2f5;
            }
        """)
        
        # Layout principal
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Espaciador superior
        layout.addStretch()
        
        # === LOGO / TÍTULO ===
        logo_frame = QFrame()
        logo_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 30px;
            }
        """)
        logo_layout = QVBoxLayout(logo_frame)
        
        titulo = QLabel("📦 KARDEX VALORIZADO")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        
        subtitulo = QLabel("Sistema de Gestión de Inventarios")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setFont(QFont("Arial", 11))
        subtitulo.setStyleSheet("color: #5f6368; padding-bottom: 10px;")
        
        logo_layout.addWidget(titulo)
        logo_layout.addWidget(subtitulo)
        layout.addWidget(logo_frame)
        
        # === FORMULARIO DE LOGIN ===
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 30px;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(15)
        
        # Usuario
        user_label = QLabel("Usuario")
        user_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        user_label.setStyleSheet("color: #202124;")
        
        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("Ingrese su usuario")
        self.txt_usuario.setFont(QFont("Arial", 11))
        self.txt_usuario.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #dadce0;
                border-radius: 5px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #1a73e8;
            }
        """)
        self.txt_usuario.returnPressed.connect(self.login)
        
        # Contraseña
        pass_label = QLabel("Contraseña")
        pass_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        pass_label.setStyleSheet("color: #202124;")
        
        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Ingrese su contraseña")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setFont(QFont("Arial", 11))
        self.txt_password.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #dadce0;
                border-radius: 5px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #1a73e8;
            }
        """)
        self.txt_password.returnPressed.connect(self.login)
        
        # Botón Ingresar
        self.btn_login = QPushButton("Iniciar Sesión")
        self.btn_login.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        self.btn_login.clicked.connect(self.login)
        
        # Agregar al formulario
        form_layout.addWidget(user_label)
        form_layout.addWidget(self.txt_usuario)
        form_layout.addWidget(pass_label)
        form_layout.addWidget(self.txt_password)
        form_layout.addSpacing(10)
        form_layout.addWidget(self.btn_login)
        
        layout.addWidget(form_frame)
        
        # === INFORMACIÓN DE LICENCIA ===
        self.lbl_licencia = QLabel()
        self.lbl_licencia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_licencia.setFont(QFont("Arial", 9))
        self.lbl_licencia.setStyleSheet("color: #5f6368; padding: 10px;")
        self.verificar_licencia_startup()
        layout.addWidget(self.lbl_licencia)
        
        # Espaciador inferior
        layout.addStretch()
        
        # Footer
        footer = QLabel("© 2024 Sistema Kardex Valorizado v1.0")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont("Arial", 8))
        footer.setStyleSheet("color: #9aa0a6;")
        layout.addWidget(footer)
        
        self.setLayout(layout)
        
        # Focus inicial en usuario
        self.txt_usuario.setFocus()
    
    def verificar_licencia_startup(self):
        """Verifica el estado de la licencia al iniciar"""
        try:
            licencia = self.session.query(Licencia).filter_by(activa=True).first()
            
            if not licencia:
                self.lbl_licencia.setText("⚠️ No hay licencia instalada - Sistema en modo demostración")
                self.lbl_licencia.setStyleSheet("color: #ea4335; font-weight: bold;")
                return
            
            # Calcular días restantes
            hoy = date.today()
            dias_restantes = (licencia.fecha_vencimiento - hoy).days
            
            if dias_restantes < 0:
                self.lbl_licencia.setText(f"❌ Licencia VENCIDA (hace {abs(dias_restantes)} días) - Solo consulta")
                self.lbl_licencia.setStyleSheet("color: #ea4335; font-weight: bold;")
            elif dias_restantes <= 30:
                self.lbl_licencia.setText(f"⚠️ Licencia vence en {dias_restantes} días")
                self.lbl_licencia.setStyleSheet("color: #f9ab00; font-weight: bold;")
            else:
                self.lbl_licencia.setText(f"✓ Licencia vigente ({dias_restantes} días restantes)")
                self.lbl_licencia.setStyleSheet("color: #34a853;")
                
        except Exception as e:
            self.lbl_licencia.setText("⚠️ Error al verificar licencia")
            self.lbl_licencia.setStyleSheet("color: #ea4335;")
    
    def login(self):
        """Procesa el intento de login"""
        usuario = self.txt_usuario.text().strip()
        password = self.txt_password.text()
        
        # Validaciones básicas
        if not usuario or not password:
            QMessageBox.warning(
                self,
                "Campos vacíos",
                "Por favor ingrese usuario y contraseña"
            )
            return
        
        try:
            # Buscar usuario en la base de datos
            user = self.session.query(Usuario).filter_by(
                username=usuario,
                activo=True
            ).first()
            
            if not user:
                QMessageBox.critical(
                    self,
                    "Error de autenticación",
                    "Usuario no encontrado o inactivo"
                )
                self.txt_password.clear()
                return
            
            # Verificar contraseña
            if not check_password_hash(user.password_hash, password):
                QMessageBox.critical(
                    self,
                    "Error de autenticación",
                    "Contraseña incorrecta"
                )
                self.txt_password.clear()
                return
            
            # Actualizar último acceso
            user.ultimo_acceso = datetime.now()
            self.session.commit()
            
            # Verificar estado de licencia
            licencia_vencida = self.verificar_licencia_activa()
            
            # Preparar información del usuario
            user_info = {
                'id': user.id,
                'username': user.username,
                'nombre_completo': user.nombre_completo,
                'rol': user.rol.value,
                'email': user.email,
                'licencia_vencida': licencia_vencida
            }
            
            # Mostrar mensaje de bienvenida
            if licencia_vencida:
                QMessageBox.warning(
                    self,
                    "Licencia Vencida",
                    f"Bienvenido {user.nombre_completo}\n\n"
                    "⚠️ La licencia ha vencido.\n"
                    "Solo podrás CONSULTAR información.\n\n"
                    "Contacta al administrador para renovar."
                )
            else:
                QMessageBox.information(
                    self,
                    "Bienvenido",
                    f"¡Hola {user.nombre_completo}!\n\n"
                    f"Rol: {user.rol.value}\n"
                    f"Último acceso: {user.ultimo_acceso.strftime('%d/%m/%Y %H:%M') if user.ultimo_acceso else 'Primer ingreso'}"
                )
            
            # Emitir señal de login exitoso
            self.login_exitoso.emit(user_info)
            
            # Cerrar ventana de login
            self.close()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al procesar login:\n{str(e)}"
            )
    
    def verificar_licencia_activa(self):
        """Verifica si la licencia está vencida"""
        try:
            licencia = self.session.query(Licencia).filter_by(activa=True).first()
            
            if not licencia:
                return True  # Sin licencia = vencida
            
            hoy = date.today()
            dias_restantes = (licencia.fecha_vencimiento - hoy).days
            
            return dias_restantes < 0  # True si está vencida
            
        except:
            return True  # En caso de error, considerar vencida
    
    def closeEvent(self, event):
        """Al cerrar la ventana"""
        self.session.close()
        event.accept()


# ============================================
# PRUEBA DE LA VENTANA DE LOGIN
# ============================================

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Crear ventana de login
    login = LoginWindow()
    
    # Conectar señal para ver qué usuario ingresó
    def usuario_ingreso(user_info):
        print(f"✓ Usuario autenticado: {user_info}")
    
    login.login_exitoso.connect(usuario_ingreso)
    login.show()
    
    sys.exit(app.exec())
