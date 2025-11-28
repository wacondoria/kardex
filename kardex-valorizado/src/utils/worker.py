from PyQt6.QtCore import QThread, pyqtSignal
import traceback

class WorkerThread(QThread):
    """
    Hilo genérico para ejecutar tareas en segundo plano.
    """
    finished = pyqtSignal(object)  # Emite el resultado
    error = pyqtSignal(str)        # Emite mensaje de error
    progress = pyqtSignal(str)     # Emite mensajes de progreso (opcional)

    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.target(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            # Capturar traceback completo para depuración
            tb = traceback.format_exc()
            print(f"Error en WorkerThread: {tb}")
            self.error.emit(str(e))
