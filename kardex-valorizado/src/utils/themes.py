"""
Centralización de Temas/Estilos para la Aplicación
Archivo: src/utils/themes.py
"""

def light_theme():
    """
    Retorna una hoja de estilos (stylesheet) para un tema claro, similar al original.
    """
    return """
        QWidget {
            background-color: #f5f5f5;
            color: #333;
            font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
            font-size: 10pt;
        }
        QMainWindow, QDialog {
            background-color: #f5f5f5;
        }
        QGroupBox {
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            background-color: #ffffff;
            border-radius: 8px;
            color: #1a73e8;
        }
        QLabel {
            color: #333;
        }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
            background-color: white;
            color: black;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 6px;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {
            border: 1px solid #1a73e8;
        }
        QPushButton {
            background-color: #1a73e8;
            color: white;
            font-weight: bold;
            border-radius: 4px;
            padding: 8px 16px;
            border: none;
        }
        QPushButton:hover {
            background-color: #4ca1ff;
        }
        QPushButton:pressed {
            background-color: #007acc;
        }
        QPushButton:disabled {
            background-color: #ccc;
            color: #666;
        }
        QTableWidget {
            background-color: white;
            border: 1px solid #ddd;
            gridline-color: #ddd;
            border-radius: 8px;
        }
        QHeaderView::section {
            background-color: #f1f3f4;
            color: #333;
            padding: 8px;
            border: 1px solid #ddd;
            font-weight: bold;
        }
        QTableWidget::item {
            padding: 6px;
        }
        QTableWidget::item:selected {
            background-color: #1a73e8;
            color: white;
        }
        QMenuBar {
            background-color: #f1f3f4;
        }
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        QMenu {
            background-color: #ffffff;
            border: 1px solid #ccc;
        }
        QMenu::item:selected {
            background-color: #1a73e8;
            color: white;
        }
        QToolBar {
            background-color: #f1f3f4;
            border: none;
        }
        QMessageBox {
            background-color: #ffffff;
        }
    """

def dark_theme():
    """
    Retorna una hoja de estilos (stylesheet) para un tema oscuro moderno.
    """
    return """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            border: none;
            font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
            font-size: 10pt;
        }
        QMainWindow, QDialog {
            background-color: #2b2b2b;
        }
        QGroupBox {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 8px;
            margin-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            background-color: #3c3c3c;
            border-radius: 8px;
            color: #1e90ff;
        }
        QLabel {
            color: #f0f0f0;
        }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
            background-color: #3c3c3c;
            color: #f0f0f0;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {
            border: 1px solid #1e90ff; /* Azul brillante al enfocar */
        }
        QPushButton {
            background-color: #1e90ff; /* Azul */
            color: white;
            font-weight: bold;
            border-radius: 4px;
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #4ca1ff; /* Azul más claro */
        }
        QPushButton:pressed {
            background-color: #007acc;
        }
        QPushButton:disabled {
            background-color: #555;
            color: #999;
        }
        QTableWidget {
            background-color: #3c3c3c;
            border: 1px solid #555;
            gridline-color: #555;
            border-radius: 8px;
        }
        QHeaderView::section {
            background-color: #2b2b2b;
            color: #1e90ff;
            padding: 8px;
            border: 1px solid #555;
            font-weight: bold;
        }
        QTableWidget::item {
            padding: 6px;
        }
        QTableWidget::item:selected {
            background-color: #1e90ff;
            color: white;
        }
        QMenuBar {
            background-color: #3c3c3c;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
        }
        QMenuBar::item:selected {
            background-color: #1e90ff;
        }
        QMenu {
            background-color: #3c3c3c;
            border: 1px solid #555;
        }
        QMenu::item:selected {
            background-color: #1e90ff;
        }
        QToolBar {
            background-color: #3c3c3c;
            border: none;
            padding: 5px;
            spacing: 5px;
        }
        QToolBar QPushButton {
            background-color: #4a4a4a;
            border: 1px solid #666;
        }
        QToolBar QPushButton:hover {
            background-color: #5a5a5a;
        }
        QMessageBox {
            background-color: #3c3c3c;
        }
        QMessageBox QLabel {
            color: #f0f0f0;
        }
        QMessageBox QPushButton {
            background-color: #1e90ff;
            color: white;
            min-width: 80px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: url(noop.png); /* Ocultar flecha por defecto si es necesario */
        }
        QComboBox QAbstractItemView {
            background-color: #3c3c3c;
            border: 1px solid #555;
            selection-background-color: #1e90ff;
        }
    """
