# -*- coding: utf-8 -*-
"""
Centralized styles for the application.
Use these constants instead of hardcoded stylesheets.
"""

# Estilo para botones cuadrados pequeños (ej. "Nuevo Cliente" con icono '+')
STYLE_CUADRADO_VERDE = """
    QPushButton {
        background-color: #34a853;
        color: white;
        font-weight: bold;
        font-size: 16px;
        border-radius: 5px;
        padding: 0px;
    }
    QPushButton:hover {
        background-color: #2e8b4e;
    }
"""

# Estilo para QCheckBox con indicador personalizado
STYLE_CHECKBOX_CUSTOM = """
    QCheckBox {
        font-weight: bold;
        color: #ea4335;
        spacing: 5px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #aaa;
        border-radius: 3px;
        background-color: white;
    }
    QCheckBox::indicator:checked {
        background-color: #34a853;
        border: 1px solid #2e8b4e;
        image: url(:/qt-project.org/styles/commonstyle/images/check-16.png);
    }
    QCheckBox::indicator:hover {
        border: 1px solid #1a73e8;
    }
"""

# Estilo para la ventana de Login
STYLE_LOGIN_WINDOW = """
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
"""

# Estilo para la etiqueta de licencia en Login (si se desea estandarizar)
STYLE_LOGIN_LICENCIA = "font-size: 9px; font-weight: normal; color: #555;"
