"""
Interfaz Gráfica para la Administración de Roles y Permisos
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QListWidget, QTreeWidget, QTreeWidgetItem, QSplitter,
                             QMessageBox, QInputDialog, QTabWidget)
from PyQt6.QtCore import Qt

from models.database_model import Rol, Permiso, Usuario, obtener_session
from sqlalchemy.orm import joinedload


class AdminRolesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Administración de Roles y Permisos")
        self.setMinimumSize(800, 600)

        self.session = obtener_session()
        self.setup_ui()
        self.cargar_datos_iniciales()
        self.conectar_signals()

    def conectar_signals(self):
        # Conexiones para la lista de roles
        self.roles_list.currentItemChanged.connect(self.actualizar_vista_rol_seleccionado)
        self.add_role_btn.clicked.connect(self.agregar_rol)
        self.edit_role_btn.clicked.connect(self.editar_rol)
        self.delete_role_btn.clicked.connect(self.eliminar_rol)

        # Conexión para guardar permisos
        self.save_permissions_btn.clicked.connect(self.guardar_permisos_rol)

        # Conexión para la lista de usuarios
        self.users_list.itemDoubleClicked.connect(self.asignar_rol_a_usuario)

    def setup_ui(self):
        # Layout principal
        main_layout = QHBoxLayout(self)

        # Divisor principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Panel izquierdo: Gestión de Roles y Permisos
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

        # Pestañas para Permisos y Usuarios por Rol
        self.tabs = QTabWidget()
        roles_layout.addWidget(self.tabs)

        # Pestaña de Permisos
        permissions_panel = QWidget()
        permissions_layout = QVBoxLayout(permissions_panel)
        self.permissions_tree = QTreeWidget()
        self.permissions_tree.setHeaderLabel("Permisos del Rol")
        permissions_layout.addWidget(self.permissions_tree)
        self.save_permissions_btn = QPushButton("💾 Guardar Permisos")
        permissions_layout.addWidget(self.save_permissions_btn)
        permissions_panel.setLayout(permissions_layout)

        # Pestaña de Usuarios Asignados
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

        # Panel derecho: Asignación de Roles a Usuarios
        users_panel = QWidget()
        users_layout = QVBoxLayout(users_panel)

        users_label = QLabel("<b>Usuarios del Sistema</b>")
        users_layout.addWidget(users_label)

        self.users_list = QListWidget()
        users_layout.addWidget(self.users_list)

        splitter.addWidget(users_panel)

        self.setLayout(main_layout)

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
        usuarios = self.session.query(Usuario).options(joinedload(Usuario.rol)).all()
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
            # Guardar el objeto permiso en el item
            item.setData(0, Qt.ItemDataRole.UserRole, permiso)
        self.permissions_tree.sortItems(0, Qt.SortOrder.AscendingOrder)

    def actualizar_vista_rol_seleccionado(self, current_item, previous_item):
        # Desmarcar todos los permisos primero
        for i in range(self.permissions_tree.topLevelItemCount()):
            item = self.permissions_tree.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)

        self.users_in_role_list.clear()

        if not current_item:
            return

        nombre_rol = current_item.text()
        rol = self.session.query(Rol).filter_by(nombre=nombre_rol).options(
            joinedload(Rol.permisos),
            joinedload(Rol.usuarios)
        ).first()

        if not rol:
            return

        # Marcar los permisos del rol seleccionado
        permisos_rol_ids = {p.id for p in rol.permisos}
        for i in range(self.permissions_tree.topLevelItemCount()):
            item = self.permissions_tree.topLevelItem(i)
            permiso = item.data(0, Qt.ItemDataRole.UserRole)
            if permiso and permiso.id in permisos_rol_ids:
                item.setCheckState(0, Qt.CheckState.Checked)

        # Cargar usuarios del rol seleccionado
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
            self.cargar_usuarios() # Para actualizar el nombre del rol en la lista de usuarios
            QMessageBox.information(self, "Éxito", "Rol actualizado.")

    def eliminar_rol(self):
        item_seleccionado = self.roles_list.currentItem()
        if not item_seleccionado:
            QMessageBox.warning(self, "Atención", "Selecciona un rol para eliminar.")
            return

        nombre_rol = item_seleccionado.text()

        # Validación: No permitir eliminar el rol Administrador
        if nombre_rol == "Administrador":
            QMessageBox.critical(self, "Error", "El rol 'Administrador' no puede ser eliminado.")
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
        if not usuario:
            return

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

            # Recargar todo para reflejar los cambios
            self.cargar_roles()
            self.cargar_usuarios()

            # Volver a seleccionar el rol que estaba activo
            if self.roles_list.currentItem():
                self.actualizar_vista_rol_seleccionado(self.roles_list.currentItem(), None)

            QMessageBox.information(self, "Éxito", f"Rol de {username} actualizado a {nuevo_rol_nombre}.")

    def closeEvent(self, event):
        self.session.close()
        super().closeEvent(event)
