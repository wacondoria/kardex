import os
import shutil
from pathlib import Path
from datetime import datetime
from utils.config import Config

class FileManager:
    """Gestor de archivos para el sistema"""
    
    @staticmethod
    def get_media_dir():
        return Path(Config.get_media_root())
    
    @staticmethod
    def ensure_directories():
        """Asegura que existan los directorios necesarios"""
        media_dir = FileManager.get_media_dir()
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / "detalle_equipos").mkdir(exist_ok=True)
        (media_dir / "salida_equipos").mkdir(exist_ok=True)
        (media_dir / "devolucion_equipos").mkdir(exist_ok=True)

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
        
        media_dir = FileManager.get_media_dir()
        destination = media_dir / category / new_filename
        
        shutil.copy2(source, destination)
        
        # Retornamos la ruta relativa para guardar en BD
        # OJO: Si usamos ruta compartida, quizás sea mejor guardar ruta absoluta o relativa al root compartido
        # Por compatibilidad, guardamos relativa al media_root, pero al recuperar reconstruimos
        return str(destination)

    @staticmethod
    def is_video(path):
        """Verifica si el archivo es un video basado en la extensión"""
        return Path(path).suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']

    @staticmethod
    def get_full_path(path_str):
        """Obtiene la ruta absoluta de un archivo guardado"""
        if not path_str:
            return None
        return str(Path(path_str).absolute())
