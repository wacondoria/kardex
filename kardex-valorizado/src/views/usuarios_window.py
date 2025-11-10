"""
Gestión de Usuarios - Sistema Kardex Valorizado
Archivo: src/views/usuarios_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QComboBox, QMessageBox, QDialog,
                              QFormLayout, QHeaderView, QGroupBox, QCheckBox,
                              QTabWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, Usuario, RolUsuario, 
                                   Empresa, UsuarioEmpresa)
from utils.widgets import UpperLineEdit
from utils.button_utils import style_button


class UsuarioDialog(QDialog):
    """Diálogo para crear/editar usuarios"""
    
    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.usuario = usuario
        self.init_ui()
        
        if usuario:
            self.cargar_datos_usuario()
    
    def init_ui(self):
        self.setWindowTitle("Nuevo Usuario" if not self.usuario else "Editar Usuario")
        self.setMinimumSize(700, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
                background-color: white;
                color: black;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #1a73e8;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #1a73e8;
                selection-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        titulo = QLabel("👤 " + ("Nuevo Usuario" if not self.usuario else "Editar Usuario"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)
        
        # Tabs
        tabs = QTabWidget()
        
        # === TAB 1: DATOS DEL USUARIO ===
        tab_datos = QWidget()
        datos_layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Username
        self.txt_username = UpperLineEdit()
        self.txt_username.setPlaceholderText("Usuario para iniciar sesión")
        self.txt_username.setMaxLength(50)
        form_layout.addRow("Usuario:*", self.txt_username)
        
        if self.usuario:
            self.txt_username.setEnabled(False)
        
        # Contraseña
        password_layout = QHBoxLayout()
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Mínimo 6 caracteres")
        
        self.txt_password_confirm = QLineEdit()
        self.txt_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password_confirm.setPlaceholderText("Confirmar contraseña")
        
        password_layout.addWidget(self.txt_password)
        password_layout.addWidget(self.txt_password_confirm)
        
        if self.usuario:
            form_layout.addRow("Nueva Contraseña:", password_layout)
            nota_pass = QLabel("(Dejar en blanco para mantener la actual)")
            nota_pass.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
            form_layout.addRow("", nota_pass)
        else:
            form_layout.addRow("Contraseña:*", password_layout)
        
        # Nombre Completo
        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre completo del usuario")
        form_layout.addRow("Nombre Completo:*", self.txt_nombre)
        
        # Email
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("correo@ejemplo.com")
        form_layout.addRow("Email:", self.txt_email)
        
        # Rol
        self.cmb_rol = QComboBox()
        self.cmb_rol.addItem("👤 Operador - Solo registros básicos", RolUsuario.OPERADOR.value)
        self.cmb_rol.addItem("👔 Supervisor - Registros y reportes", RolUsuario.SUPERVISOR.value)
        self.cmb_rol.addItem("👑 Administrador - Acceso total", RolUsuario.ADMINISTRADOR.value)
        form_layout.addRow("Rol:*", self.cmb_rol)
        
        datos_layout.addLayout(form_layout)
        datos_layout.addStretch()
        
        tab_datos.setLayout(datos_layout)
        tabs.addTab(tab_datos, "📋 Datos Básicos")
        
        # === TAB 2: EMPRESAS Y PERMISOS ===
        tab_empresas = QWidget()
        empresas_layout = QVBoxLayout()
        
        info_label = QLabel("Seleccione las empresas a las que tendrá acceso este usuario:")
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        empresas_layout.addWidget(info_label)
        
        # Lista de empresas con checkboxes
        self.lista_empresas = []
        empresas = self.session.query(Empresa).filter_by(activo=True).all()
        
        for emp in empresas:
            grupo_empresa = QGroupBox(f"🏢 {emp.razon_social}")
            grupo_layout = QVBoxLayout()
            
            chk_acceso = QCheckBox("✓ Tiene acceso a esta empresa")
            chk_acceso.setStyleSheet("font-weight: bold; color: #1a73e8;")
            
            # Permisos específicos
            permisos_layout = QHBoxLayout()
            
            chk_registrar = QCheckBox("Puede registrar")
            chk_registrar.setChecked(True)
            
            chk_modificar = QCheckBox("Puede modificar")
            
            chk_eliminar = QCheckBox("Puede eliminar")
            
            chk_reportes = QCheckBox("Ver reportes")
            chk_reportes.setChecked(True)
            
            # Habilitar/deshabilitar permisos según acceso
            def toggle_permisos(estado, controles):
                for control in controles:
                    control.setEnabled(estado)
            
            controles_permisos = [chk_registrar, chk_modificar, chk_eliminar, chk_reportes]
            chk_acceso.toggled.connect(lambda state, c=controles_permisos: toggle_permisos(state, c))
            
            # Inicialmente deshabilitados
            for control in controles_permisos:
                control.setEnabled(False)
            
            permisos_layout.addWidget(chk_registrar)
            permisos_layout.addWidget(chk_modificar)
            permisos_layout.addWidget(chk_eliminar)
            permisos_layout.addWidget(chk_reportes)
            permisos_layout.addStretch()
            
            grupo_layout.addWidget(chk_acceso)
            grupo_layout.addLayout(permisos_layout)
            
            grupo_empresa.setLayout(grupo_layout)
            empresas_layout.addWidget(grupo_empresa)
            
            self.lista_empresas.append({
                'empresa_id': emp.id,
                'chk_acceso': chk_acceso,
                'chk_registrar': chk_registrar,
                'chk_modificar': chk_modificar,
                'chk_eliminar': chk_eliminar,
                'chk_reportes': chk_reportes
            })
        
        empresas_layout.addStretch()
        tab_empresas.setLayout(empresas_layout)
        tabs.addTab(tab_empresas, "🏢 Empresas y Permisos")
        
        layout.addWidget(tabs)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f4;
                color: #333;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_guardar = QPushButton("Guardar Usuario")
        btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        btn_guardar.clicked.connect(self.guardar)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def keyPressEvent(self, event):
        """Captura la pulsación de teclas en el diálogo."""
        if event.key() == Qt.Key.Key_F4:
            self.guardar()
        else:
            super().keyPressEvent(event)

    def cargar_datos_usuario(self):
        """Carga datos del usuario en edición"""
        self.txt_username.setText(self.usuario.username)
        self.txt_nombre.setText(self.usuario.nombre_completo)
        self.txt_email.setText(self.usuario.email or "")
        
        # Seleccionar rol
        for i in range(self.cmb_rol.count()):
            if self.cmb_rol.itemData(i) == self.usuario.rol.value:
                self.cmb_rol.setCurrentIndex(i)
                break
        
        # Cargar empresas asignadas
        empresas_usuario = self.session.query(UsuarioEmpresa).filter_by(
            usuario_id=self.usuario.id
        ).all()
        
        for emp_data in self.lista_empresas:
            empresa_asignada = next(
                (eu for eu in empresas_usuario if eu.empresa_id == emp_data['empresa_id']),
                None
            )
            
            if empresa_asignada:
                emp_data['chk_acceso'].setChecked(True)
                emp_data['chk_registrar'].setChecked(empresa_asignada.puede_registrar)
                emp_data['chk_modificar'].setChecked(empresa_asignada.puede_modificar)
                emp_data['chk_eliminar'].setChecked(empresa_asignada.puede_eliminar)
                emp_data['chk_reportes'].setChecked(empresa_asignada.puede_ver_reportes)
    
    def guardar(self):
        """Guarda el usuario"""
        # Validaciones
        username = self.txt_username.text().strip()
        nombre = self.txt_nombre.text().strip()
        password = self.txt_password.text()
        password_confirm = self.txt_password_confirm.text()
        
        if not username or not nombre:
            QMessageBox.warning(self, "Error", "Usuario y nombre completo son obligatorios")
            return
        
        if not self.usuario and not password:
            QMessageBox.warning(self, "Error", "La contraseña es obligatoria para usuarios nuevos")
            return
        
        if password:
            if len(password) < 6:
                QMessageBox.warning(self, "Error", "La contraseña debe tener al menos 6 caracteres")
                return
            
            if password != password_confirm:
                QMessageBox.warning(self, "Error", "Las contraseñas no coinciden")
                return
        
        # Validar que tenga al menos una empresa asignada
        empresas_seleccionadas = [e for e in self.lista_empresas if e['chk_acceso'].isChecked()]
        if not empresas_seleccionadas:
            QMessageBox.warning(self, "Error", "Debe asignar al menos una empresa al usuario")
            return
        
        try:
            if not self.usuario:
                # Verificar que no exista el username
                existe = self.session.query(Usuario).filter_by(username=username).first()
                if existe:
                    QMessageBox.warning(self, "Error", f"El usuario '{username}' ya existe")
                    return
                
                # Crear nuevo usuario
                usuario = Usuario(
                    username=username,
                    password_hash=generate_password_hash(password),
                    nombre_completo=nombre,
                    email=self.txt_email.text().strip() or None,
                    rol=RolUsuario(self.cmb_rol.currentData())
                )
                
                self.session.add(usuario)
                self.session.flush()
                
                mensaje = f"Usuario '{username}' creado exitosamente"
            else:
                # Editar existente
                self.usuario.nombre_completo = nombre
                self.usuario.email = self.txt_email.text().strip() or None
                self.usuario.rol = RolUsuario(self.cmb_rol.currentData())
                
                if password:
                    self.usuario.password_hash = generate_password_hash(password)
                
                usuario = self.usuario
                mensaje = f"Usuario '{username}' actualizado exitosamente"
                
                # Eliminar asignaciones anteriores
                self.session.query(UsuarioEmpresa).filter_by(usuario_id=usuario.id).delete()
            
            # Asignar empresas
            for emp_data in empresas_seleccionadas:
                asignacion = UsuarioEmpresa(
                    usuario_id=usuario.id,
                    empresa_id=emp_data['empresa_id'],
                    puede_registrar=emp_data['chk_registrar'].isChecked(),
                    puede_modificar=emp_data['chk_modificar'].isChecked(),
                    puede_eliminar=emp_data['chk_eliminar'].isChecked(),
                    puede_ver_reportes=emp_data['chk_reportes'].isChecked()
                )
                self.session.add(asignacion)
            
            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")


class UsuariosWindow(QWidget):
    """Ventana principal de gestión de usuarios"""
    
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.usuarios_mostrados = []
        self.init_ui()
        self.cargar_usuarios()

    def keyPressEvent(self, event):
        """Captura la pulsación de F2 para crear y F6 para editar."""
        if event.key() == Qt.Key.Key_F2:
            self.nuevo_usuario()
        elif event.key() == Qt.Key.Key_F6:
            fila = self.tabla.currentRow()
            if fila != -1 and fila < len(self.usuarios_mostrados):
                usuario_seleccionado = self.usuarios_mostrados[fila]
                self.editar_usuario(usuario_seleccionado)
        else:
            super().keyPressEvent(event)
    
    def init_ui(self):
        self.setWindowTitle("Gestión de Usuarios")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("👥 Gestión de Usuarios")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        btn_nuevo = QPushButton()
        style_button(btn_nuevo, 'add', "Nuevo Usuario")
        btn_nuevo.clicked.connect(self.nuevo_usuario)
        
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nuevo)
        
        # Filtro
        filtro_layout = QHBoxLayout()
        
        self.txt_buscar = UpperLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar por usuario o nombre...")
        self.txt_buscar.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
            }
        """)
        self.txt_buscar.textChanged.connect(self.buscar_usuarios)
        
        filtro_layout.addWidget(self.txt_buscar)
        
        # Contador
        self.lbl_contador = QLabel()
        self.lbl_contador.setStyleSheet("color: #666; font-size: 11px;")
        
        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "Usuario", "Nombre Completo", "Email", "Rol", "Empresas", "Estado", "Acciones"
        ])
        
        self.tabla.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f1f3f4;
                padding: 10px;
                font-weight: bold;
            }
        """)
        
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(6, 200)
        
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addLayout(header_layout)
        layout.addLayout(filtro_layout)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)
        
        self.setLayout(layout)
    
    def cargar_usuarios(self):
        """Carga todos los usuarios"""
        usuarios = self.session.query(Usuario).order_by(Usuario.username).all()
        self.mostrar_usuarios(usuarios)
    
    def mostrar_usuarios(self, usuarios):
        """Muestra usuarios en la tabla"""
        self.usuarios_mostrados = usuarios
        self.tabla.setRowCount(len(usuarios))
        
        for row, user in enumerate(usuarios):
            # Username
            self.tabla.setItem(row, 0, QTableWidgetItem(user.username))
            
            # Nombre
            self.tabla.setItem(row, 1, QTableWidgetItem(user.nombre_completo))
            
            # Email
            self.tabla.setItem(row, 2, QTableWidgetItem(user.email or ""))
            
            # Rol
            rol_texto = {
                RolUsuario.ADMINISTRADOR: "👑 Administrador",
                RolUsuario.SUPERVISOR: "👔 Supervisor",
                RolUsuario.OPERADOR: "👤 Operador"
            }
            self.tabla.setItem(row, 3, QTableWidgetItem(rol_texto[user.rol]))
            
            # Empresas asignadas
            empresas = self.session.query(UsuarioEmpresa).filter_by(usuario_id=user.id).count()
            self.tabla.setItem(row, 4, QTableWidgetItem(f"{empresas} empresa(s)"))
            
            # Estado
            estado = "✓ Activo" if user.activo else "✕ Inactivo"
            item_estado = QTableWidgetItem(estado)
            if user.activo:
                item_estado.setForeground(Qt.GlobalColor.darkGreen)
            else:
                item_estado.setForeground(Qt.GlobalColor.red)
            self.tabla.setItem(row, 5, item_estado)
            
            # Botones
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 5, 5, 5)
            
            btn_editar = QPushButton()
            style_button(btn_editar, 'edit', "Editar")
            btn_editar.clicked.connect(lambda checked, u=user: self.editar_usuario(u))
            
            btn_toggle = QPushButton("Activar" if not user.activo else "Desactivar")
            btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #f9ab00;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
            """)
            btn_toggle.clicked.connect(lambda checked, u=user: self.toggle_usuario(u))
            
            btn_layout.addWidget(btn_editar)
            btn_layout.addWidget(btn_toggle)
            btn_widget.setLayout(btn_layout)
            
            self.tabla.setCellWidget(row, 6, btn_widget)
        
        self.lbl_contador.setText(f"📊 Total: {len(usuarios)} usuario(s)")
    
    def buscar_usuarios(self):
        """Busca usuarios por texto"""
        texto = self.txt_buscar.text().lower()
        
        usuarios = self.session.query(Usuario).all()
        
        if texto:
            usuarios = [u for u in usuarios if 
                       texto in u.username.lower() or 
                       texto in u.nombre_completo.lower()]
        
        self.mostrar_usuarios(usuarios)
    
    def nuevo_usuario(self):
        """Abre diálogo para crear usuario"""
        dialog = UsuarioDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_usuarios()
    
    def editar_usuario(self, usuario):
        """Abre diálogo para editar usuario"""
        dialog = UsuarioDialog(self, usuario)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(usuario)
            self.cargar_usuarios()
    
    def toggle_usuario(self, usuario):
        """Activa/desactiva un usuario"""
        accion = "desactivar" if usuario.activo else "activar"
        
        respuesta = QMessageBox.question(
            self,
            "Confirmar",
            f"¿{accion.capitalize()} usuario '{usuario.username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                usuario.activo = not usuario.activo
                self.session.commit()
                QMessageBox.information(self, "Éxito", f"Usuario {accion}do correctamente")
                self.cargar_usuarios()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    ventana = UsuariosWindow()
    ventana.resize(1200, 700)
    ventana.show()
    
    sys.exit(app.exec())
