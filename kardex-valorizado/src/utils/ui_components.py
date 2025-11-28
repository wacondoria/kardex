from PyQt6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
from PyQt6.QtGui import QColor, QPalette

class StandardTable(QTableWidget):
    """
    Tabla estandarizada para la aplicación.
    Configura automáticamente:
    - Colores alternos
    - Selección por filas
    - Estilo de cabecera
    - Comportamiento de selección
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        # Comportamiento
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Solo lectura por defecto
        
        # Cabecera
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Estilo
        # Nota: Los colores específicos deberían venir de un tema centralizado si es posible,
        # pero por ahora definimos un estilo limpio aquí.
        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #e0e0e0;
                selection-background-color: #e8f0fe;
                selection-color: #1a73e8;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 6px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
                color: #5f6368;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
