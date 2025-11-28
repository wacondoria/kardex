from apscheduler.schedulers.background import BackgroundScheduler
from services.backup_manager import BackupManager
from datetime import datetime
import atexit

class BackupScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.backup_manager = BackupManager()
        self.scheduler.add_job(self.ejecutar_backup_diario, 'cron', hour=13, minute=0) # 1:00 PM
        
    def start(self):
        try:
            self.scheduler.start()
            print("📅 Programador de backups iniciado.")
            atexit.register(lambda: self.scheduler.shutdown())
        except Exception as e:
            print(f"Error al iniciar scheduler: {e}")

    def ejecutar_backup_diario(self):
        print("⏳ Ejecutando backup automático programado...")
        exito, nombre, _ = self.backup_manager.crear_backup(
            tipo='automatico', 
            descripcion=f'Backup automático programado - {datetime.now().strftime("%d/%m/%Y")}'
        )
        if exito:
            print(f"✅ Backup automático completado: {nombre}")
        else:
            print(f"❌ Error en backup automático: {nombre}")
