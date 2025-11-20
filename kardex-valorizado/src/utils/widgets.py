"""
Widgets personalizados para la aplicación Kardex Valorizado.
Archivo: src/utils/widgets.py
"""

from PyQt6.QtWidgets import QLineEdit, QComboBox, QCompleter, QStyledItemDelegate, QStyle
from PyQt6.QtGui import QValidator
from PyQt6.QtCore import Qt

class SearchableComboBox(QComboBox):
    """
    Un QComboBox con funcionalidad de búsqueda incorporada.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)

        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompleter(self.completer)

        self.lineEdit().textEdited.connect(self._update_model)
        self.currentIndexChanged.connect(self._on_index_changed)

    def wheelEvent(self, e):
        if not self.view().isVisible():
            e.ignore()
        else:
            super().wheelEvent(e)

    def _update_model(self, text):
        # Cada vez que el texto cambia, actualizamos el modelo del completer
        # para que siempre se base en la lista completa de ítems.
        model = self.model()
        self.completer.setModel(model)

    def _on_index_changed(self, index):
        # Cuando se selecciona un ítem, nos aseguramos de que el modelo del
        # completer se resetee para la próxima vez que el usuario escriba.
        model = self.model()
        self.completer.setModel(model)

    def addItem(self, text, userData=None):
        super().addItem(text, userData)
        self._update_model_source()

    def addItems(self, texts):
        super().addItems(texts)
        self._update_model_source()

    def clear(self):
        super().clear()
        self._update_model_source()

    def _update_model_source(self):
        # Esta es la clave para que el completer siempre tenga la lista completa.
        # Se llama cada vez que los ítems del ComboBox cambian.
        self.completer.setModel(self.model())


class UppercaseValidator(QValidator):
    def validate(self, input_str, pos):
        return (QValidator.State.Acceptable, input_str.upper(), pos)

class UpperLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(UppercaseValidator())

class MoneyDelegate(QStyledItemDelegate):
    """
    Delegado para pintar celdas con importes monetarios.
    Alinea el símbolo de moneda a la izquierda y el monto a la derecha.
    Si no hay símbolo, solo alinea el monto a la derecha.
    """
    def paint(self, painter, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            super().paint(painter, option, index)
            return

        text = str(text)
        symbol = ""
        amount = text

        # Detectar símbolo (asume S/ o $)
        # Caso típico: "S/ 1,234.56" o "$ 1,234.56"
        if "S/" in text:
            symbol = "S/"
            amount = text.replace("S/", "").strip()
        elif "$" in text:
            symbol = "$"
            amount = text.replace("$", "").strip()

        painter.save()

        # Dibujar fondo (manejar selección)
        if option.state & QStyle.State.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        rect = option.rect
        # Márgenes internos
        rect.adjust(5, 0, -5, 0)

        # Dibujar Símbolo (Izquierda)
        if symbol:
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, symbol)

        # Dibujar Monto (Derecha)
        painter.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, amount)

        painter.restore()
