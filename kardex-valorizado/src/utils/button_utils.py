"""
Utilidades para estilizar botones de forma centralizada.
Archivo: src/utils/button_utils.py
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize
import sys
from pathlib import Path

# Asegurarse de que el directorio raíz del proyecto esté en el sys.path
# para que los recursos se puedan encontrar de manera confiable.
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Definición de colores estándar
COLORS = {
    'edit': '#28a745',      # Verde
    'delete': '#dc3545',    # Rojo
    'view': '#007bff',      # Azul
    'edit_hover': '#218838',
    'delete_hover': '#c82333',
    'view_hover': '#0069d9'
}

# Definición de rutas a los íconos
BASE_PATH = Path(__file__).resolve().parent.parent
ICON_PATHS = {
    'edit': str(BASE_PATH / 'resources/edit.png'),
    'delete': str(BASE_PATH / 'resources/delete.png'),
    'view': str(BASE_PATH / 'resources/view.png')
}

def style_button(button: QPushButton, button_type: str, text: str = ""):
    """
    Aplica un estilo estandarizado a un QPushButton.

    Args:
        button: El botón (QPushButton) al que se aplicará el estilo.
        button_type: El tipo de botón ('edit', 'delete', 'view').
        text: El texto a mostrar en el botón. Si está vacío, solo se mostrará el ícono.
    """
    if button_type not in COLORS or button_type not in ICON_PATHS:
        print(f"ADVERTENCIA: Tipo de botón '{button_type}' no reconocido.")
        return

    # --- Configuración del Ícono ---
    icon_path = ICON_PATHS[button_type]
    if Path(icon_path).exists():
        icon = QIcon(QPixmap(icon_path))
        button.setIcon(icon)
        button.setIconSize(QSize(16, 16)) # Tamaño estándar para el ícono
    else:
        print(f"ADVERTENCIA: No se encontró el ícono en la ruta: {icon_path}")
        # Si no hay ícono, usar un caracter de respaldo
        fallback_chars = {'edit': 'E', 'delete': 'X', 'view': 'V'}
        button.setText(fallback_chars.get(button_type, '?'))

    # --- Configuración del Texto y ToolTip ---
    if text:
        button.setText(text)
        button.setToolTip(text)
    else:
        # Si no hay texto, el tooltip es más descriptivo
        tooltips = {
            'edit': 'Editar registro',
            'delete': 'Eliminar registro',
            'view': 'Ver detalle'
        }
        button.setToolTip(tooltips.get(button_type, 'Acción'))

    # --- Hoja de Estilo (Stylesheet) ---
    color = COLORS[button_type]
    hover_color = COLORS[f"{button_type}_hover"]
    stylesheet = f"""
        QPushButton {{
            background-color: {color};
            color: white;
            padding: 5px 8px;
            border-radius: 4px;
            border: none;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:disabled {{
            background-color: #cccccc;
            color: #666666;
        }}
    """
    button.setStyleSheet(stylesheet)
    button.setMinimumHeight(28) # Altura mínima estándar
