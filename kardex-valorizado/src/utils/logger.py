import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger():
    """
    Configura el logger de la aplicación.
    Crea un directorio 'logs' si no existe y configura un RotatingFileHandler.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "app.log"
    
    # Configuración básica
    logger = logging.getLogger("KardexApp")
    logger.setLevel(logging.INFO)
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler de archivo (Rotativo: 5MB, mantiene 3 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Handler de consola (opcional, útil para desarrollo)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Evitar duplicar handlers si se llama varias veces
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    logger.info("Logger inicializado correctamente.")
    return logger

def get_logger(name=None):
    """Retorna un logger hijo o el logger raíz de la app"""
    if name:
        return logging.getLogger(f"KardexApp.{name}")
    return logging.getLogger("KardexApp")
