"""
Contexto de Aplicación Global
Mantiene el estado compartido a través de toda la aplicación,
como el año contable seleccionado y la información del usuario.
"""

class _AppContext:
    """
    Clase interna que gestiona el estado. Se instancia una sola vez.
    """
    def __init__(self):
        self.user_info = None
        self.selected_year = None
        self.main_window = None
        self.session = None
        self.empresa = None
        self.user_permissions = set()

    def set_user_info(self, user_info):
        """Guarda la información del usuario logueado."""
        self.user_info = user_info

    def get_user_info(self):
        """Devuelve la información del usuario."""
        return self.user_info

    def set_user_permissions(self, permissions):
        """
        Guarda los permisos del usuario actual.
        'permissions' debe ser un iterable de strings (claves de permiso).
        """
        self.user_permissions = set(permissions)
        print(f"🔑 Permisos de usuario cargados: {self.user_permissions}")

    def has_permission(self, permission_key):
        """
        Verifica si el usuario actual tiene un permiso específico.
        Permite acceso total si el permiso 'acceso_total' está presente.
        """
        if "acceso_total" in self.user_permissions:
            return True
        return permission_key in self.user_permissions

    def set_selected_year(self, year):
        """Guarda el año contable seleccionado."""
        self.selected_year = year
        print(f"✅ Año de trabajo establecido en: {self.selected_year}")

    def get_selected_year(self):
        """Devuelve el año contable seleccionado."""
        return self.selected_year

    def set_main_window(self, window):
        """Guarda una referencia a la ventana principal."""
        self.main_window = window

    def get_main_window(self):
        """Devuelve la referencia a la ventana principal."""
        return self.main_window

    def set_session(self, session):
        """Guarda la sesión de SQLAlchemy."""
        self.session = session

    def get_session(self):
        """Devuelve la sesión de SQLAlchemy."""
        return self.session

    def set_empresa(self, empresa):
        """Guarda la empresa seleccionada."""
        self.empresa = empresa

    def get_empresa(self):
        """Devuelve la empresa seleccionada."""
        return self.empresa

# Instancia única (Singleton) que será importada por otras partes de la app.
# Ejemplo de uso: from utils.app_context import app_context
app_context = _AppContext()
