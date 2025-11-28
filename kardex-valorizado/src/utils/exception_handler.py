import sys
import traceback
from PyQt6.QtWidgets import QMessageBox
from utils.logger import get_logger

logger = get_logger("ExceptionHandler")

def setup_exception_hook():
    """
    Configura el hook global de excepciones para capturar crashes no controlados.
    """
    sys.excepthook = exception_hook

def exception_hook(exctype, value, tb):
    """
    Manejador global de excepciones.
    Loguea el error y muestra un mensaje amigable al usuario.
    """
    # Ignorar interrupciones de teclado (Ctrl+C)
    if exctype is KeyboardInterrupt:
        sys.__excepthook__(exctype, value, tb)
        return

    # Formatear traza
    traceback_str = "".join(traceback.format_exception(exctype, value, tb))
    
    # Loguear error crítico
    logger.critical(f"Excepción no controlada: {value}\n{traceback_str}")
    
    # Mostrar mensaje al usuario (si hay interfaz gráfica activa)
    try:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error Inesperado")
        msg.setText("Ha ocurrido un error inesperado en la aplicación.")
        msg.setInformativeText("El error ha sido registrado. Por favor contacte a soporte.")
        msg.setDetailedText(traceback_str)
        msg.exec()
    except:
        # Si falla mostrar el mensaje (ej. error en Qt), al menos ya está logueado
        print("Error crítico (no se pudo mostrar alerta GUI):", value)
        print(traceback_str)
