import os
import shutil
from pathlib import Path
from datetime import datetime

class FileManager:
    """Gestor de archivos para el sistema"""
    
    BASE_DIR = Path("user_data")
    BASE_DIR = Path("user_data")
    MEDIA_DIR = BASE_DIR / "media"
    
    @staticmethod
    def ensure_directories():
        """Asegura que existan los directorios necesarios"""
        FileManager.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        (FileManager.MEDIA_DIR / "detalle_equipos").mkdir(exist_ok=True)
        (FileManager.MEDIA_DIR / "salida_equipos").mkdir(exist_ok=True)
        (FileManager.MEDIA_DIR / "devolucion_equipos").mkdir(exist_ok=True)

    @staticmethod
    def save_file(source_path, category, prefix="file"):
        """
        Copia un archivo (foto/video) al directorio gestionado.
        category: 'detalle_equipos', 'salida_equipos', 'devolucion_equipos'
        prefix: prefijo para el nombre del archivo
        """
        FileManager.ensure_directories()
        
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {source_path}")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = source.suffix
        new_filename = f"{prefix}_{timestamp}{extension}"
        
        destination = FileManager.MEDIA_DIR / category / new_filename
        
        shutil.copy2(source, destination)
        
        # Retornamos la ruta relativa para guardar en BD
        return str(destination)

    @staticmethod
    def is_video(path):
        """Verifica si el archivo es un video basado en la extensión"""
        return Path(path).suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']

    @staticmethod
    def get_full_path(relative_path):
        """Obtiene la ruta absoluta de un archivo guardado"""
        if not relative_path:
            return None
        return str(Path(relative_path).absolute())
