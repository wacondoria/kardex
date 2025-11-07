"""
Widgets personalizados para la aplicación Kardex Valorizado.
Archivo: src/utils/widgets.py
"""

from PyQt6.QtWidgets import QLineEdit, QComboBox, QCompleter
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
