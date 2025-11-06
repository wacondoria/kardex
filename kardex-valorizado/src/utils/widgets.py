"""
Widgets personalizados para la aplicación Kardex Valorizado.
Archivo: src/utils/widgets.py
"""

from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QValidator

class UppercaseValidator(QValidator):
    def validate(self, input_str, pos):
        return (QValidator.State.Acceptable, input_str.upper(), pos)

class UpperLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(UppercaseValidator())
