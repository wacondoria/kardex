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
    'add': '#28a745',       # Verde para 'add'
    'edit_hover': '#218838',
    'delete_hover': '#c82333',
    'view_hover': '#0069d9',
    'add_hover': '#218838'
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
        button_type: El tipo de botón ('edit', 'delete', 'view', 'add').
        text: El texto a mostrar en el botón.
    """
    if button_type not in COLORS:
        print(f"ADVERTENCIA: Tipo de botón '{button_type}' no reconocido.")
        return

    # --- Lógica de Estilo ---
    if button_type == 'add':
        # Para 'add', usamos un símbolo de texto '+' en lugar de un ícono de archivo.
        if text:
            button.setText(f"+ {text}")
    else:
        # Para otros tipos, buscamos un ícono en los recursos.
        if button_type in ICON_PATHS:
            icon_path = ICON_PATHS[button_type]
            if Path(icon_path).exists():
                icon = QIcon(QPixmap(icon_path))
                button.setIcon(icon)
                button.setIconSize(QSize(16, 16))
            else:
                print(f"ADVERTENCIA: No se encontró el ícono en la ruta: {icon_path}")

        button.setText(text)

    # --- Configuración del ToolTip ---
    tooltips = {
        'edit': 'Editar registro',
        'delete': 'Eliminar registro',
        'view': 'Ver detalle',
        'add': f'Añadir nuevo {text}' if text else 'Añadir nuevo registro'
    }
    button.setToolTip(tooltips.get(button_type, text or 'Acción'))

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
