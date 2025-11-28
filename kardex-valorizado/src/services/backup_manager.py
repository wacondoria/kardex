from pathlib import Path
from datetime import datetime
import shutil
import json
import os

class BackupManager:
    """Gestor de backups"""
    
    def __init__(self, db_path='data/kardex.db', backup_dir='backups'):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = 10
    
    def crear_backup(self, tipo='manual', descripcion=''):
        """Crea un backup de la base de datos"""
        try:
            if not self.db_path.exists():
                return False, "Base de datos no encontrada", None
            
            # Nombre del archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_backup = f"kardex_backup_{tipo}_{timestamp}.db"
            ruta_backup = self.backup_dir / nombre_backup
            
            # Copiar base de datos
            shutil.copy2(self.db_path, ruta_backup)
            
            # Guardar metadatos
            metadata = {
                'fecha': datetime.now().isoformat(),
                'tipo': tipo,
                'descripcion': descripcion,
                'tamanio_bytes': ruta_backup.stat().st_size,
                'archivo': nombre_backup
            }
            
            metadata_path = ruta_backup.with_suffix('.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Limpiar backups antiguos
            self._limpiar_backups_antiguos()
            
            return True, nombre_backup, metadata
            
        except Exception as e:
            return False, f"Error: {str(e)}", None
    
    def _limpiar_backups_antiguos(self):
        """Mantiene solo los últimos N backups"""
        backups = sorted(self.backup_dir.glob('kardex_backup_*.db'))
        
        if len(backups) > self.max_backups:
            backups_a_eliminar = backups[:-self.max_backups]
            for backup in backups_a_eliminar:
                backup.unlink()
                # Eliminar metadatos
                metadata = backup.with_suffix('.json')
                if metadata.exists():
                    metadata.unlink()
    
    def listar_backups(self):
        """Lista todos los backups disponibles"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('kardex_backup_*.db'), reverse=True):
            metadata_file = backup_file.with_suffix('.json')
            
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                # Crear metadatos básicos si no existen
                metadata = {
                    'fecha': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                    'tipo': 'desconocido',
                    'descripcion': '',
                    'tamanio_bytes': backup_file.stat().st_size,
                    'archivo': backup_file.name
                }
            
            backups.append(metadata)
        
        return backups
    
    def restaurar_backup(self, nombre_backup):
        """Restaura la base de datos desde un backup"""
        try:
            ruta_backup = self.backup_dir / nombre_backup
            
            if not ruta_backup.exists():
                return False, f"Backup {nombre_backup} no encontrado"
            
            # Crear backup de seguridad antes de restaurar
            self.crear_backup(tipo='pre_restauracion', 
                            descripcion='Backup automático antes de restaurar')
            
            # Restaurar
            shutil.copy2(ruta_backup, self.db_path)
            
            return True, "Restauración exitosa"
            
        except Exception as e:
            return False, f"Error al restaurar: {str(e)}"
