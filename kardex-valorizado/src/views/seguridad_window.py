"""
Gestión de Seguridad (Usuarios, Roles y Permisos) - Sistema Kardex Valorizado
Archivo: src/views/seguridad_window.py
(Módulo unificado de usuarios_window.py y admin_roles_window.py)
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QComboBox, QMessageBox, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QCheckBox,
                             QTabWidget, QListWidget, QTreeWidget, QTreeWidgetItem, 
                             QSplitter, QInputDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.orm import joinedload

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import (obtener_session, Usuario, Rol,
                                   Empresa, Permiso)
from utils.widgets import UpperLineEdit
from utils.button_utils import style_button


# =======================================================================
# DIÁLOGO DE USUARIO (SIMPLIFICADO)
# (Ya no maneja roles, solo datos de usuario y empresas)
# =======================================================================

class UsuarioDialog(QDialog):
    """Diálogo para crear/editar usuarios (Datos y Empresas)"""
    
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
            QDialog { background-color: #f5f5f5; }
            QLineEdit, QComboBox {
                padding: 8px; border: 2px solid #ddd;
                border-radius: 4px; background-color: white; color: black;
            }
            QLineEdit:focus, QComboBox:focus { border: 2px solid #1a73e8; }
            QComboBox QAbstractItemView {
                background-color: white; color: black;
                selection-background-color: #1a73e8; selection-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        titulo = QLabel("👤 " + ("Nuevo Usuario" if not self.usuario else "Editar Usuario"))
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8; padding: 10px;")
        layout.addWidget(titulo)
        
        tabs = QTabWidget()
        
        # === TAB 1: DATOS DEL USUARIO ===
        tab_datos = QWidget()
        datos_layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.txt_username = UpperLineEdit()
        self.txt_username.setPlaceholderText("Usuario para iniciar sesión")
        self.txt_username.setMaxLength(50)
        form_layout.addRow("Usuario:*", self.txt_username)
        
        if self.usuario:
            self.txt_username.setEnabled(False)
        
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
        
        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre completo del usuario")
        form_layout.addRow("Nombre Completo:*", self.txt_nombre)
        
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("correo@ejemplo.com")
        form_layout.addRow("Email:", self.txt_email)
        
        # --- CAMBIO ---
        # El QComboBox de Rol se ha eliminado de aquí.
        # La asignación de roles se hace en la Pestaña 2 de la ventana principal.
        
        datos_layout.addLayout(form_layout)
        datos_layout.addStretch()
        tab_datos.setLayout(datos_layout)
        tabs.addTab(tab_datos, "📋 Datos Básicos")
        
        # === TAB 2: EMPRESAS ASIGNADAS ===
        tab_empresas = QWidget()
        empresas_layout = QVBoxLayout()
        info_label = QLabel("Seleccione las empresas a las que tendrá acceso este usuario:")
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        empresas_layout.addWidget(info_label)
        
        self.lista_empresas_chks = []
        empresas = self.session.query(Empresa).filter_by(activo=True).all()
        
        for emp in empresas:
            chk_empresa = QCheckBox(f"🏢 {emp.razon_social}")
            chk_empresa.setStyleSheet("font-weight: bold; color: #1a73e8; padding: 5px;")
            empresas_layout.addWidget(chk_empresa)
            self.lista_empresas_chks.append({'empresa': emp, 'checkbox': chk_empresa})
        
        empresas_layout.addStretch()
        tab_empresas.setLayout(empresas_layout)
        tabs.addTab(tab_empresas, "🏢 Empresas Asignadas")
        
        layout.addWidget(tabs)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_guardar = QPushButton("Guardar Usuario")
        style_button(btn_guardar, 'add', "Guardar Usuario")
        btn_guardar.clicked.connect(self.guardar)
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4:
            self.guardar()
        else:
            super().keyPressEvent(event)

    def cargar_datos_usuario(self):
        self.txt_username.setText(self.usuario.username)
        self.txt_nombre.setText(self.usuario.nombre_completo)
        self.txt_email.setText(self.usuario.email or "")
        
        # --- CAMBIO ---
        # Ya no se carga el rol aquí
        
        empresas_usuario_ids = {emp.id for emp in self.usuario.empresas}
        for item in self.lista_empresas_chks:
            if item['empresa'].id in empresas_usuario_ids:
                item['checkbox'].setChecked(True)
    
    def guardar(self):
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
        
        empresas_seleccionadas = [item['empresa'] for item in self.lista_empresas_chks if item['checkbox'].isChecked()]
        if not empresas_seleccionadas:
            QMessageBox.warning(self, "Error", "Debe asignar al menos una empresa al usuario")
            return
        
        try:
            # --- CAMBIO ---
            # Ya no se asigna el 'rol_id_seleccionado' aquí
            
            if not self.usuario:
                existe = self.session.query(Usuario).filter_by(username=username).first()
                if existe:
                    QMessageBox.warning(self, "Error", f"El usuario '{username}' ya existe")
                    return
                
                usuario = Usuario(
                    username=username,
                    password_hash=generate_password_hash(password),
                    nombre_completo=nombre,
                    email=self.txt_email.text().strip() or None
                    # rol_id se asignará desde la otra pestaña
                )
                self.session.add(usuario)
                mensaje = f"Usuario '{username}' creado exitosamente"
            else:
                self.usuario.nombre_completo = nombre
                self.usuario.email = self.txt_email.text().strip() or None
                if password:
                    self.usuario.password_hash = generate_password_hash(password)
                
                usuario = self.usuario
                mensaje = f"Usuario '{username}' actualizado exitosamente"
            
            usuario.empresas = empresas_seleccionadas
            
            self.session.commit()
            QMessageBox.information(self, "Éxito", mensaje)
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")


# =======================================================================
# PESTAÑA 1: GESTIÓN DE USUARIOS
# (Lógica de la antigua 'UsuariosWindow')
# =======================================================================

class UsuariosTab(QWidget):
    
    def __init__(self, roles_tab_ref=None):
        super().__init__()
        self.session = obtener_session()
        self.usuarios_mostrados = []
        self.roles_tab_ref = roles_tab_ref # Referencia a la otra pestaña
        self.init_ui()
        self.cargar_usuarios()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2:
            self.nuevo_usuario()
        elif event.key() == Qt.Key.Key_F6:
            fila = self.tabla.currentRow()
            if fila != -1 and fila < len(self.usuarios_mostrados):
                self.editar_usuario(self.usuarios_mostrados[fila])
        else:
            super().keyPressEvent(event)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        titulo = QLabel("Gestión de Cuentas de Usuario")
        titulo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        btn_nuevo = QPushButton()
        style_button(btn_nuevo, 'add', "Nuevo Usuario (F2)")
        btn_nuevo.clicked.connect(self.nuevo_usuario)
        
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_nuevo)
        
        filtro_layout = QHBoxLayout()
        self.txt_buscar = UpperLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar por usuario o nombre...")
        self.txt_buscar.setStyleSheet("padding: 10px; border: 2px solid #ddd; border-radius: 5px;")
        self.txt_buscar.textChanged.connect(self.buscar_usuarios)
        filtro_layout.addWidget(self.txt_buscar)
        
        self.lbl_contador = QLabel()
        self.lbl_contador.setStyleSheet("color: #666; font-size: 11px;")
        
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels(
            ["Usuario", "Nombre Completo", "Email", "Rol", "Empresas", "Estado", "Acciones"]
        )
        self.tabla.setStyleSheet("""
            QTableWidget { border: 1px solid #ddd; border-radius: 5px; background-color: white; }
            QHeaderView::section { background-color: #f1f3f4; padding: 10px; font-weight: bold; }
        """)
        
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(6, 200)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addLayout(header_layout)
        layout.addLayout(filtro_layout)
        layout.addWidget(self.lbl_contador)
        layout.addWidget(self.tabla)
    
    def cargar_usuarios(self):
        self.session.expire_all()
        usuarios = self.session.query(Usuario).options(
            joinedload(Usuario.rol), 
            joinedload(Usuario.empresas)
        ).order_by(Usuario.username).all()
        self.mostrar_usuarios(usuarios)
    
    def mostrar_usuarios(self, usuarios):
        self.usuarios_mostrados = usuarios
        self.tabla.setRowCount(len(usuarios))
        
        for row, user in enumerate(usuarios):
            self.tabla.setItem(row, 0, QTableWidgetItem(user.username))
            self.tabla.setItem(row, 1, QTableWidgetItem(user.nombre_completo))
            self.tabla.setItem(row, 2, QTableWidgetItem(user.email or ""))
            
            rol_nombre = user.rol.nombre if user.rol else "Sin Asignar"
            self.tabla.setItem(row, 3, QTableWidgetItem(f"👑 {rol_nombre}"))
            
            empresas_count = len(user.empresas)
            self.tabla.setItem(row, 4, QTableWidgetItem(f"{empresas_count} empresa(s)"))
            
            estado = "✓ Activo" if user.activo else "✕ Inactivo"
            item_estado = QTableWidgetItem(estado)
            item_estado.setForeground(Qt.GlobalColor.darkGreen if user.activo else Qt.GlobalColor.red)
            self.tabla.setItem(row, 5, item_estado)
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 5, 5, 5)
            
            btn_editar = QPushButton()
            style_button(btn_editar, 'edit', "Editar (F6)")
            btn_editar.clicked.connect(lambda checked, u=user: self.editar_usuario(u))
            
            btn_toggle = QPushButton("Activar" if not user.activo else "Desactivar")
            btn_toggle.setStyleSheet("background-color: #f9ab00; color: white; padding: 5px 10px; border-radius: 3px;")
            btn_toggle.clicked.connect(lambda checked, u=user: self.toggle_usuario(u))
            
            btn_layout.addWidget(btn_editar)
            btn_layout.addWidget(btn_toggle)
            btn_widget.setLayout(btn_layout)
            
            self.tabla.setCellWidget(row, 6, btn_widget)
        
        self.lbl_contador.setText(f"📊 Total: {len(usuarios)} usuario(s)")
    
    def buscar_usuarios(self):
        texto = self.txt_buscar.text().strip()
        query = self.session.query(Usuario).options(
            joinedload(Usuario.rol), 
            joinedload(Usuario.empresas)
        )
        if texto:
            search_text = f"%{texto}%"
            query = query.filter(
                (Usuario.username.ilike(search_text)) |
                (Usuario.nombre_completo.ilike(search_text))
            )
        usuarios = query.order_by(Usuario.username).all()
        self.mostrar_usuarios(usuarios)
    
    def nuevo_usuario(self):
        dialog = UsuarioDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_usuarios()
            # Actualizar la otra pestaña
            if self.roles_tab_ref:
                self.roles_tab_ref.cargar_usuarios()
    
    def editar_usuario(self, usuario):
        dialog = UsuarioDialog(self, usuario)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session.refresh(usuario)
            self.cargar_usuarios()
            # Actualizar la otra pestaña
            if self.roles_tab_ref:
                self.roles_tab_ref.cargar_usuarios()
    
    def toggle_usuario(self, usuario):
        accion = "desactivar" if usuario.activo else "activar"
        respuesta = QMessageBox.question(
            self, "Confirmar",
            f"¿{accion.capitalize()} usuario '{usuario.username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                usuario.activo = not usuario.activo
                self.session.commit()
                QMessageBox.information(self, "Éxito", f"Usuario {accion}do correctamente")
                self.cargar_usuarios()
                # Actualizar la otra pestaña
                if self.roles_tab_ref:
                    self.roles_tab_ref.cargar_usuarios()
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")


# =======================================================================
# PESTAÑA 2: GESTIÓN DE ROLES Y PERMISOS
# (Lógica de la antigua 'AdminRolesWindow')
# =======================================================================

class RolesTab(QWidget):
    
    def __init__(self, usuarios_tab_ref=None):
        super().__init__()
        self.session = obtener_session()
        self.usuarios_tab_ref = usuarios_tab_ref # Referencia a la otra pestaña
        self.setup_ui()
        self.cargar_datos_iniciales()
        self.conectar_signals()

    def conectar_signals(self):
        self.roles_list.currentItemChanged.connect(self.actualizar_vista_rol_seleccionado)
        self.add_role_btn.clicked.connect(self.agregar_rol)
        self.edit_role_btn.clicked.connect(self.editar_rol)
        self.delete_role_btn.clicked.connect(self.eliminar_rol)
        self.save_permissions_btn.clicked.connect(self.guardar_permisos_rol)
        self.users_list.itemDoubleClicked.connect(self.asignar_rol_a_usuario)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        roles_panel = QWidget()
        roles_layout = QVBoxLayout(roles_panel)
        roles_label = QLabel("<b>Roles del Sistema</b>")
        roles_layout.addWidget(roles_label)
        self.roles_list = QListWidget()
        roles_layout.addWidget(self.roles_list)

        roles_buttons_layout = QHBoxLayout()
        self.add_role_btn = QPushButton("➕ Añadir Rol")
        self.edit_role_btn = QPushButton("✏️ Editar Rol")
        self.delete_role_btn = QPushButton("❌ Eliminar Rol")
        roles_buttons_layout.addWidget(self.add_role_btn)
        roles_buttons_layout.addWidget(self.edit_role_btn)
        roles_buttons_layout.addWidget(self.delete_role_btn)
        roles_layout.addLayout(roles_buttons_layout)

        self.tabs = QTabWidget()
        roles_layout.addWidget(self.tabs)

        permissions_panel = QWidget()
        permissions_layout = QVBoxLayout(permissions_panel)
        self.permissions_tree = QTreeWidget()
        self.permissions_tree.setHeaderLabel("Permisos del Rol")
        permissions_layout.addWidget(self.permissions_tree)
        self.save_permissions_btn = QPushButton("💾 Guardar Permisos")
        permissions_layout.addWidget(self.save_permissions_btn)
        permissions_panel.setLayout(permissions_layout)

        users_in_role_panel = QWidget()
        users_in_role_layout = QVBoxLayout(users_in_role_panel)
        users_in_role_label = QLabel("<b>Usuarios con este Rol</b>")
        self.users_in_role_list = QListWidget()
        users_in_role_layout.addWidget(users_in_role_label)
        users_in_role_layout.addWidget(self.users_in_role_list)
        users_in_role_panel.setLayout(users_in_role_layout)

        self.tabs.addTab(permissions_panel, "🔑 Permisos")
        self.tabs.addTab(users_in_role_panel, "👥 Usuarios Asignados")
        splitter.addWidget(roles_panel)

        users_panel = QWidget()
        users_layout = QVBoxLayout(users_panel)
        users_label = QLabel("<b>Usuarios del Sistema</b> (Doble clic para asignar rol)")
        users_layout.addWidget(users_label)
        self.users_list = QListWidget()
        users_layout.addWidget(self.users_list)
        splitter.addWidget(users_panel)
        
        splitter.setSizes([400, 300])

    def cargar_datos_iniciales(self):
        self.cargar_roles()
        self.cargar_usuarios()
        self.cargar_permisos_arbol()

    def cargar_roles(self):
        self.roles_list.clear()
        roles = self.session.query(Rol).options(joinedload(Rol.permisos), joinedload(Rol.usuarios)).all()
        for rol in roles:
            self.roles_list.addItem(f"{rol.nombre}")
        self.roles_list.sortItems()

    def cargar_usuarios(self):
        self.users_list.clear()
        usuarios = self.session.query(Usuario).options(joinedload(Usuario.rol)).filter(Usuario.activo == True).all()
        for usuario in usuarios:
            rol_nombre = usuario.rol.nombre if usuario.rol else "Sin rol"
            self.users_list.addItem(f"{usuario.username} ({rol_nombre})")
        self.users_list.sortItems()

    def cargar_permisos_arbol(self):
        self.permissions_tree.clear()
        permisos = self.session.query(Permiso).all()
        for permiso in permisos:
            item = QTreeWidgetItem(self.permissions_tree)
            item.setText(0, permiso.descripcion)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, permiso)
        self.permissions_tree.sortItems(0, Qt.SortOrder.AscendingOrder)

    def actualizar_vista_rol_seleccionado(self, current_item, previous_item):
        for i in range(self.permissions_tree.topLevelItemCount()):
            item = self.permissions_tree.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)
        self.users_in_role_list.clear()
        if not current_item: return

        nombre_rol = current_item.text()
        rol = self.session.query(Rol).filter_by(nombre=nombre_rol).options(
            joinedload(Rol.permisos), joinedload(Rol.usuarios)
        ).first()
        if not rol: return

        permisos_rol_ids = {p.id for p in rol.permisos}
        for i in range(self.permissions_tree.topLevelItemCount()):
            item = self.permissions_tree.topLevelItem(i)
            permiso = item.data(0, Qt.ItemDataRole.UserRole)
            if permiso and permiso.id in permisos_rol_ids:
                item.setCheckState(0, Qt.CheckState.Checked)

        for usuario in rol.usuarios:
            self.users_in_role_list.addItem(usuario.username)
        self.users_in_role_list.sortItems()

    def agregar_rol(self):
        nombre, ok = QInputDialog.getText(self, "Añadir Rol", "Nombre del nuevo rol:")
        if ok and nombre:
            if self.session.query(Rol).filter_by(nombre=nombre).first():
                QMessageBox.warning(self, "Error", f"El rol '{nombre}' ya existe.")
                return
            nuevo_rol = Rol(nombre=nombre)
            self.session.add(nuevo_rol)
            self.session.commit()
            self.cargar_roles()
            QMessageBox.information(self, "Éxito", f"Rol '{nombre}' creado.")

    def editar_rol(self):
        item_seleccionado = self.roles_list.currentItem()
        if not item_seleccionado:
            QMessageBox.warning(self, "Atención", "Selecciona un rol para editar.")
            return
        nombre_actual = item_seleccionado.text()
        rol = self.session.query(Rol).filter_by(nombre=nombre_actual).first()

        nuevo_nombre, ok = QInputDialog.getText(self, "Editar Rol", "Nuevo nombre:", text=nombre_actual)
        if ok and nuevo_nombre and nuevo_nombre != nombre_actual:
            if self.session.query(Rol).filter_by(nombre=nuevo_nombre).first():
                QMessageBox.warning(self, "Error", f"El rol '{nuevo_nombre}' ya existe.")
                return
            rol.nombre = nuevo_nombre
            self.session.commit()
            self.cargar_roles()
            self.cargar_usuarios()
            QMessageBox.information(self, "Éxito", "Rol actualizado.")

    def eliminar_rol(self):
        item_seleccionado = self.roles_list.currentItem()
        if not item_seleccionado:
            QMessageBox.warning(self, "Atención", "Selecciona un rol para eliminar.")
            return
        nombre_rol = item_seleccionado.text()
        if nombre_rol == "ADMINISTRADOR":
            QMessageBox.critical(self, "Error", "El rol 'ADMINISTRADOR' no puede ser eliminado.")
            return
        rol = self.session.query(Rol).filter_by(nombre=nombre_rol).options(joinedload(Rol.usuarios)).first()
        if rol.usuarios:
            QMessageBox.warning(self, "Error", "No se puede eliminar un rol con usuarios asignados.")
            return
        
        confirmar = QMessageBox.question(self, "Confirmar", f"¿Estás seguro de que quieres eliminar el rol '{nombre_rol}'?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirmar == QMessageBox.StandardButton.Yes:
            self.session.delete(rol)
            self.session.commit()
            self.cargar_roles()
            QMessageBox.information(self, "Éxito", f"Rol '{nombre_rol}' eliminado.")

    def guardar_permisos_rol(self):
        item_seleccionado = self.roles_list.currentItem()
        if not item_seleccionado:
            QMessageBox.warning(self, "Atención", "Selecciona un rol para guardar sus permisos.")
            return
        nombre_rol = item_seleccionado.text()
        rol = self.session.query(Rol).filter_by(nombre=nombre_rol).first()

        permisos_seleccionados = []
        for i in range(self.permissions_tree.topLevelItemCount()):
            item = self.permissions_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                permiso = item.data(0, Qt.ItemDataRole.UserRole)
                if permiso:
                    permisos_seleccionados.append(permiso)
        
        rol.permisos = permisos_seleccionados
        self.session.commit()
        QMessageBox.information(self, "Éxito", f"Permisos para el rol '{nombre_rol}' actualizados.")

    def asignar_rol_a_usuario(self, item):
        username = item.text().split(" ")[0]
        usuario = self.session.query(Usuario).filter_by(username=username).first()
        if not usuario: return

        roles = self.session.query(Rol).order_by(Rol.nombre).all()
        nombres_roles = [rol.nombre for rol in roles]
        rol_actual_nombre = usuario.rol.nombre if usuario.rol else ""
        
        try:
            indice_actual = nombres_roles.index(rol_actual_nombre) if rol_actual_nombre in nombres_roles else 0
        except ValueError:
            indice_actual = 0

        nuevo_rol_nombre, ok = QInputDialog.getItem(self, "Asignar Rol",
                                                    f"Seleccionar rol para {username}:",
                                                    nombres_roles, indice_actual, False)

        if ok and nuevo_rol_nombre != rol_actual_nombre:
            nuevo_rol = self.session.query(Rol).filter_by(nombre=nuevo_rol_nombre).first()
            usuario.rol = nuevo_rol
            self.session.commit()
            
            # Recargar todo
            self.cargar_usuarios()
            if self.roles_list.currentItem():
                self.actualizar_vista_rol_seleccionado(self.roles_list.currentItem(), None)
            
            # Actualizar la otra pestaña
            if self.usuarios_tab_ref:
                self.usuarios_tab_ref.cargar_usuarios()
                
            QMessageBox.information(self, "Éxito", f"Rol de {username} actualizado a {nuevo_rol_nombre}.")

# =======================================================================
# VENTANA CONTENEDORA PRINCIPAL
# =======================================================================

class SeguridadWindow(QWidget):
    
    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info # Guardar user_info si se necesita
        
        self.setWindowTitle("Administración de Seguridad")
        self.setMinimumSize(1200, 700)

        # Crear un layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear el QTabWidget
        self.tabs = QTabWidget()
        
        # Crear las pestañas
        self.tab_usuarios = UsuariosTab(None)
        self.tab_roles = RolesTab(self.tab_usuarios) # Pasar la referencia
        
        # Pasar la referencia circular
        self.tab_usuarios.roles_tab_ref = self.tab_roles

        # Añadir las pestañas al QTabWidget
        self.tabs.addTab(self.tab_usuarios, "👥 Gestión de Usuarios")
        self.tabs.addTab(self.tab_roles, "🔑 Gestión de Roles y Permisos")
        
        # Añadir el QTabWidget al layout principal
        main_layout.addWidget(self.tabs)
        
        # Aplicar un estilo al QTabWidget para que se vea bien
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 10px 25px;
                font-weight: bold;
                font-size: 11px;
                background-color: #e0e0e0;
                color: #555;
            }
            QTabBar::tab:selected {
                background-color: #1a73e8;
                color: white;
            }
            QTabWidget::pane {
                border-top: 2px solid #1a73e8;
            }
        """)

    def closeEvent(self, event):
        """Asegurarse de cerrar las sesiones de las pestañas."""
        if hasattr(self.tab_usuarios, 'session'):
            self.tab_usuarios.session.close()
        if hasattr(self.tab_roles, 'session'):
            self.tab_roles.session.close()
        super().closeEvent(event)


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Simular user_info
    simulated_user_info = {'rol': 'ADMINISTRADOR'}
    
    ventana = SeguridadWindow(user_info=simulated_user_info)
    ventana.show()
    
    sys.exit(app.exec())