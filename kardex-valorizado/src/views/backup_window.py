"""
Sistema de Backup y Restauración - Sistema Kardex Valorizado
Archivo: src/views/backup_window.py
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QMessageBox, QHeaderView, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.backup_manager import BackupManager

class BackupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.backup_manager = BackupManager()
        self.init_ui()
        self.cargar_backups()
        
        # Timer para backup automático (cada hora verificar)
        self.timer_auto_backup = QTimer()
        self.timer_auto_backup.timeout.connect(self.verificar_backup_automatico)
        self.timer_auto_backup.start(3600000)  # 1 hora en milisegundos
    
    def init_ui(self):
        self.setWindowTitle("Sistema de Backup y Restauración")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        titulo = QLabel("💾 Sistema de Backup y Restauración")
        titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #1a73e8;")
        
        header_layout.addWidget(titulo)
        header_layout.addStretch()
        
        # Botones de acción
        btn_backup_manual = QPushButton("📦 Crear Backup Ahora")
        btn_backup_manual.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                padding: 12px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
        """)
        btn_backup_manual.clicked.connect(self.crear_backup_manual)
        
        btn_actualizar = QPushButton("🔄 Actualizar Lista")
        btn_actualizar.setStyleSheet("""
            QPushButton {
                background-color: #34a853;
                color: white;
                padding: 12px 25px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        btn_actualizar.clicked.connect(self.cargar_backups)
        
        header_layout.addWidget(btn_actualizar)
        header_layout.addWidget(btn_backup_manual)
        
        layout.addLayout(header_layout)
        
        # Advertencia
        warning = QLabel(
            "⚠️ IMPORTANTE: Los backups se guardan automáticamente cada 24 horas y antes de cada restauración.\n"
            "Se mantienen los últimos 10 backups. Las restauraciones NO se pueden deshacer."
        )
        warning.setStyleSheet("""
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            color: #856404;
            border: 2px solid #ffc107;
        """)
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        # Información del sistema
        info_layout = QHBoxLayout()
        
        self.lbl_db_size = QLabel()
        self.lbl_db_size.setStyleSheet("padding: 10px; background-color: #e8f0fe; border-radius: 5px;")
        
        self.lbl_backup_count = QLabel()
        self.lbl_backup_count.setStyleSheet("padding: 10px; background-color: #e8f0fe; border-radius: 5px;")
        
        self.lbl_ultimo_backup = QLabel()
        self.lbl_ultimo_backup.setStyleSheet("padding: 10px; background-color: #e8f0fe; border-radius: 5px;")
        
        info_layout.addWidget(self.lbl_db_size)
        info_layout.addWidget(self.lbl_backup_count)
        info_layout.addWidget(self.lbl_ultimo_backup)
        
        layout.addLayout(info_layout)
        
        # Tabla de backups
        tabla_label = QLabel("📋 Backups Disponibles:")
        tabla_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(tabla_label)
        
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            "Fecha/Hora", "Tipo", "Descripción", "Tamaño", "Archivo", "Acciones"
        ])
        
        self.tabla.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #1a73e8;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(5, 120)
        
        self.tabla.setAlternatingRowColors(True)
        
        layout.addWidget(self.tabla)
        
        # Progress bar (oculta por defecto)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #1a73e8;
            }
        """)
        layout.addWidget(self.progress)
        
        self.setLayout(layout)
        self.actualizar_info_sistema()
    
    def actualizar_info_sistema(self):
        """Actualiza la información del sistema"""
        # Tamaño BD
        db_path = Path('data/kardex.db')
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            self.lbl_db_size.setText(f"📊 Base de Datos: {size_mb:.2f} MB")
        else:
            self.lbl_db_size.setText("📊 Base de Datos: No encontrada")
        
        # Cantidad de backups
        backups = self.backup_manager.listar_backups()
        self.lbl_backup_count.setText(f"💾 Backups: {len(backups)} de {self.backup_manager.max_backups}")
        
        # Último backup
        if backups:
            ultimo = backups[0]
            fecha = datetime.fromisoformat(ultimo['fecha'])
            self.lbl_ultimo_backup.setText(f"🕐 Último Backup: {fecha.strftime('%d/%m/%Y %H:%M')}")
        else:
            self.lbl_ultimo_backup.setText("🕐 Último Backup: Ninguno")
    
    def cargar_backups(self):
        """Carga la lista de backups"""
        backups = self.backup_manager.listar_backups()
        
        self.tabla.setRowCount(len(backups))
        
        for row, backup in enumerate(backups):
            # Fecha
            fecha = datetime.fromisoformat(backup['fecha'])
            item_fecha = QTableWidgetItem(fecha.strftime('%d/%m/%Y %H:%M:%S'))
            item_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(row, 0, item_fecha)
            
            # Tipo
            tipo_texto = {
                'manual': '🔷 Manual',
                'automatico': '⚡ Automático',
                'pre_restauracion': '⚠️ Pre-Restauración',
                'desconocido': '❓ Desconocido'
            }
            item_tipo = QTableWidgetItem(tipo_texto.get(backup['tipo'], backup['tipo']))
            item_tipo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(row, 1, item_tipo)
            
            # Descripción
            self.tabla.setItem(row, 2, QTableWidgetItem(backup.get('descripcion', '')))
            
            # Tamaño
            size_mb = backup['tamanio_bytes'] / (1024 * 1024)
            item_size = QTableWidgetItem(f"{size_mb:.2f} MB")
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(row, 3, item_size)
            
            # Archivo
            self.tabla.setItem(row, 4, QTableWidgetItem(backup['archivo']))
            
            # Botón restaurar
            btn_restaurar = QPushButton("↩️ Restaurar")
            btn_restaurar.setStyleSheet("""
                QPushButton {
                    background-color: #f9ab00;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e69500;
                }
            """)
            btn_restaurar.clicked.connect(lambda checked, b=backup: self.restaurar_backup(b))
            
            self.tabla.setCellWidget(row, 5, btn_restaurar)
        
        self.actualizar_info_sistema()
    
    def crear_backup_manual(self):
        """Crea un backup manual"""
        respuesta = QMessageBox.question(
            self,
            "Crear Backup",
            "¿Desea crear un backup de la base de datos ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            self.progress.setVisible(True)
            self.progress.setValue(0)
            
            # Simular progreso
            for i in range(0, 101, 20):
                self.progress.setValue(i)
                QTimer.singleShot(50 * i, lambda: None)  # Pequeña pausa visual
            
            exito, mensaje, metadata = self.backup_manager.crear_backup(
                tipo='manual',
                descripcion='Backup manual creado por el usuario'
            )
            
            self.progress.setValue(100)
            
            if exito:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"✅ Backup creado exitosamente:\n\n{mensaje}\n\n"
                    f"Tamaño: {metadata['tamanio_bytes'] / (1024*1024):.2f} MB"
                )
                self.cargar_backups()
            else:
                QMessageBox.critical(self, "Error", f"❌ Error al crear backup:\n{mensaje}")
            
            self.progress.setVisible(False)
    
    def restaurar_backup(self, backup):
        """Restaura un backup"""
        respuesta = QMessageBox.warning(
            self,
            "⚠️ CONFIRMAR RESTAURACIÓN",
            f"⚠️ ADVERTENCIA IMPORTANTE ⚠️\n\n"
            f"Está a punto de restaurar el backup:\n"
            f"• Fecha: {datetime.fromisoformat(backup['fecha']).strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"• Tipo: {backup['tipo']}\n\n"
            f"🔴 ESTO SOBRESCRIBIRÁ LA BASE DE DATOS ACTUAL\n"
            f"🔴 TODOS LOS CAMBIOS POSTERIORES A ESE BACKUP SE PERDERÁN\n\n"
            f"Se creará un backup automático antes de restaurar.\n\n"
            f"¿Está completamente seguro de continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            # Doble confirmación
            confirmacion = QMessageBox.question(
                self,
                "Segunda Confirmación",
                "Esta es su última oportunidad para cancelar.\n\n"
                "¿Confirma que desea restaurar el backup?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirmacion == QMessageBox.StandardButton.Yes:
                self.progress.setVisible(True)
                self.progress.setValue(0)
                
                for i in range(0, 101, 25):
                    self.progress.setValue(i)
                    QTimer.singleShot(50 * i, lambda: None)
                
                exito, mensaje = self.backup_manager.restaurar_backup(backup['archivo'])
                
                self.progress.setValue(100)
                
                if exito:
                    QMessageBox.information(
                        self,
                        "✅ Restauración Exitosa",
                        f"La base de datos ha sido restaurada exitosamente.\n\n"
                        f"⚠️ IMPORTANTE: Debe REINICIAR la aplicación para que los cambios tengan efecto.\n\n"
                        f"Cierre el sistema completamente y vuelva a abrirlo."
                    )
                    self.cargar_backups()
                else:
                    QMessageBox.critical(self, "Error", f"❌ Error en restauración:\n{mensaje}")
                
                self.progress.setVisible(False)
    
    def verificar_backup_automatico(self):
        """Verifica si hay que hacer backup automático"""
        backups = self.backup_manager.listar_backups()
        
        # Si no hay backups o el último es de hace más de 24 horas
        if not backups:
            self.crear_backup_automatico()
        else:
            ultimo = backups[0]
            fecha_ultimo = datetime.fromisoformat(ultimo['fecha'])
            ahora = datetime.now()
            
            # Si han pasado más de 24 horas
            if (ahora - fecha_ultimo).total_seconds() > 86400:
                self.crear_backup_automatico()
    
    def crear_backup_automatico(self):
        """Crea un backup automático"""
        exito, mensaje, metadata = self.backup_manager.crear_backup(
            tipo='automatico',
            descripcion=f'Backup automático diario - {datetime.now().strftime("%d/%m/%Y")}'
        )
        
        if exito:
            print(f"✓ Backup automático creado: {mensaje}")
            self.cargar_backups()


# PRUEBA STANDALONE
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    ventana = BackupWindow()
    ventana.resize(1100, 700)
    ventana.show()
    
    sys.exit(app.exec())