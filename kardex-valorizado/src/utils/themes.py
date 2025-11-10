# -*- coding: utf-8 -*-
"""
Módulo para la gestión de temas (claro/oscuro) de la aplicación.
"""

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

DARK_THEME_STYLESHEET = """
    QWidget {{
        background-color: #2d2d2d;
        color: #f0f0f0;
        font-family: Arial;
    }}
    QMainWindow {{
        background-color: #2d2d2d;
    }}
    QMenuBar {{
        background-color: #3d3d3d;
        color: #f0f0f0;
    }}
    QMenuBar::item {{
        background-color: #3d3d3d;
        color: #f0f0f0;
    }}
    QMenuBar::item:selected {{
        background-color: #555;
    }}
    QMenu {{
        background-color: #3d3d3d;
        color: #f0f0f0;
        border: 1px solid #555;
    }}
    QMenu::item:selected {{
        background-color: #555;
    }}
    QToolBar {{
        background-color: #353535;
        border: none;
        padding: 5px;
        spacing: 5px;
    }}
    QLabel {{
        background-color: transparent;
        color: #f0f0f0;
    }}
    QPushButton {{
        background-color: #555;
        color: #f0f0f0;
        border: 1px solid #666;
        border-radius: 5px;
        padding: 8px 15px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: #666;
        border: 1px solid #777;
    }}
    QPushButton:pressed {{
        background-color: #444;
    }}
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
        background-color: #3d3d3d;
        color: #f0f0f0;
        border: 1px solid #666;
        border-radius: 4px;
        padding: 5px;
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
        border: 1px solid #0078d7;
    }}
    QComboBox::drop-down {{
        border-left: 1px solid #666;
    }}
    QComboBox QAbstractItemView {{
        background-color: #3d3d3d;
        color: #f0f0f0;
        selection-background-color: #555;
        border: 1px solid #666;
    }}
    QTableWidget {{
        background-color: #3d3d3d;
        color: #f0f0f0;
        gridline-color: #555;
        border: 1px solid #666;
    }}
    QHeaderView::section {{
        background-color: #444;
        color: #f0f0f0;
        padding: 4px;
        border: 1px solid #555;
        font-weight: bold;
    }}
    QTabWidget::pane {{
        border-top: 2px solid #555;
    }}
    QTabBar::tab {{
        background: #3d3d3d;
        border: 1px solid #555;
        padding: 10px;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
    }}
    QTabBar::tab:selected {{
        background: #2d2d2d;
        border-top: 2px solid #0078d7;
        border-bottom: 2px solid #2d2d2d;
    }}
    QTabBar::tab:!selected {{
        margin-top: 2px;
    }}
    QScrollBar:vertical {{
        border: 1px solid #444;
        background: #3d3d3d;
        width: 15px;
        margin: 15px 0 15px 0;
    }}
    QScrollBar::handle:vertical {{
        background: #555;
        min-height: 20px;
    }}
    QScrollBar:horizontal {{
        border: 1px solid #444;
        background: #3d3d3d;
        height: 15px;
        margin: 0 15px 0 15px;
    }}
    QScrollBar::handle:horizontal {{
        background: #555;
        min-width: 20px;
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 16px;
        border-left: 1px solid #666;
        border-bottom: 1px solid #666;
        background-color: #3d3d3d;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
        background-color: #555;
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 16px;
        border-left: 1px solid #666;
        border-top: 1px solid #666;
        background-color: #3d3d3d;
    }}
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: #555;
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        width: 10px;
        height: 10px;
        image: url({base_path}/kardex-valorizado/src/resources/icons/white/cil-arrow-top.svg);
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        width: 10px;
        height: 10px;
        image: url({base_path}/kardex-valorizado/src/resources/icons/white/cil-arrow-bottom.svg);
    }}
"""

LIGHT_THEME_STYLESHEET = """
    QWidget {{
        background-color: #f8f9fa;
        color: #212529;
        font-family: Arial;
    }}
    QMainWindow {{
        background-color: #f8f9fa;
    }}
    QMenuBar {{
        background-color: #e9ecef;
        color: #212529;
    }}
    QMenuBar::item {{
        background-color: #e9ecef;
    }}
    QMenuBar::item:selected {{
        background-color: #dee2e6;
    }}
    QMenu {{
        background-color: #ffffff;
        color: #212529;
        border: 1px solid #ced4da;
    }}
    QMenu::item:selected {{
        background-color: #e9ecef;
    }}
    QToolBar {{
        background-color: #f1f3f4;
        border: none;
        padding: 5px;
        spacing: 5px;
    }}
    QLabel {{
        background-color: transparent;
        color: #212529;
    }}
    QPushButton {{
        background-color: #ffffff;
        border: 1px solid #ced4da;
        border-radius: 5px;
        padding: 8px 15px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: #e8f0fe;
        border: 1px solid #0078d7;
    }}
    QPushButton:pressed {{
        background-color: #dbeaff;
    }}
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
        background-color: #ffffff;
        color: #212529;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 5px;
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
        border: 1px solid #0078d7;
    }}
    QComboBox::drop-down {{
        border-left: 1px solid #ced4da;
    }}
    QComboBox QAbstractItemView {{
        background-color: #ffffff;
        color: #212529;
        selection-background-color: #e8f0fe;
        border: 1px solid #ced4da;
    }}
    QTableWidget {{
        background-color: #ffffff;
        color: #212529;
        gridline-color: #e9ecef;
        border: 1px solid #ced4da;
    }}
    QHeaderView::section {{
        background-color: #f1f3f4;
        color: #212529;
        padding: 4px;
        border: 1px solid #ced4da;
        font-weight: bold;
    }}
    QTabWidget::pane {{
        border-top: 2px solid #ced4da;
    }}
    QTabBar::tab {{
        background: #e9ecef;
        border: 1px solid #ced4da;
        padding: 10px;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
    }}
    QTabBar::tab:selected {{
        background: #f8f9fa;
        border-top: 2px solid #0078d7;
        border-bottom: 2px solid #f8f9fa;
    }}
    QTabBar::tab:!selected {{
        margin-top: 2px;
    }}
    QScrollBar:vertical {{
        border: 1px solid #dee2e6;
        background: #f1f3f4;
        width: 15px;
        margin: 15px 0 15px 0;
    }}
    QScrollBar::handle:vertical {{
        background: #ced4da;
        min-height: 20px;
    }}
    QScrollBar:horizontal {{
        border: 1px solid #dee2e6;
        background: #f1f3f4;
        height: 15px;
        margin: 0 15px 0 15px;
    }}
    QScrollBar::handle:horizontal {{
        background: #ced4da;
        min-width: 20px;
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 16px;
        border-left: 1px solid #ced4da;
        border-bottom: 1px solid #ced4da;
        background-color: #f8f9fa;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
        background-color: #e9ecef;
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 16px;
        border-left: 1px solid #ced4da;
        border-top: 1px solid #ced4da;
        background-color: #f8f9fa;
    }}
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: #e9ecef;
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        width: 10px;
        height: 10px;
        image: url({base_path}/kardex-valorizado/src/resources/icons/black/cil-arrow-top.svg);
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        width: 10px;
        height: 10px;
        image: url({base_path}/kardex-valorizado/src/resources/icons/black/cil-arrow-bottom.svg);
    }}
"""

def get_theme_stylesheet(base_path):
    """
    Detecta el tema del sistema (claro u oscuro) y devuelve la hoja de estilo
    correspondiente, formateada con la ruta base a los recursos.
    """
    app = QApplication.instance()

    # Determinar qué hoja de estilo usar
    stylesheet_template = LIGHT_THEME_STYLESHEET
    if app:
        window_color = app.palette().color(QPalette.ColorRole.Window)
        if window_color.lightness() < 128:
            print("💡 Tema oscuro detectado. Aplicando estilos oscuros.")
            stylesheet_template = DARK_THEME_STYLESHEET
        else:
            print("💡 Tema claro detectado. Aplicando estilos claros.")

    # Formatear la hoja de estilo con la ruta base
    return stylesheet_template.format(base_path=base_path)
