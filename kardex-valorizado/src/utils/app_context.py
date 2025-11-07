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

    def set_user_info(self, user_info):
        """Guarda la información del usuario logueado."""
        self.user_info = user_info

    def get_user_info(self):
        """Devuelve la información del usuario."""
        return self.user_info

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

# Instancia única (Singleton) que será importada por otras partes de la app.
# Ejemplo de uso: from utils.app_context import app_context
app_context = _AppContext()
