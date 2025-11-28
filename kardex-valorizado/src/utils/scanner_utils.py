from PyQt6.QtCore import QObject, QEvent, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

class BarcodeListener(QObject):
    """
    Escucha eventos de teclado globales o en un widget para detectar
    entrada rápida típica de un escáner de código de barras (HID).
    """
    barcode_scanned = pyqtSignal(str)

    def __init__(self, parent=None, min_chars=3, max_interval_ms=50):
        super().__init__(parent)
        self.buffer = ""
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._process_buffer)
        self.max_interval_ms = max_interval_ms
        self.min_chars = min_chars

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            # Si es un caracter imprimible
            if event.text():
                self.buffer += event.text()
                self.timer.start(self.max_interval_ms)
            # Si es Enter, procesar inmediatamente
            elif event.key() == 16777220 or event.key() == 16777221: # Enter keys
                self._process_buffer()
        
        return super().eventFilter(obj, event)

    def _process_buffer(self):
        if len(self.buffer) >= self.min_chars:
            # Limpiar buffer de caracteres no deseados (saltos de linea)
            code = self.buffer.strip()
            if code:
                self.barcode_scanned.emit(code)
        self.buffer = ""
