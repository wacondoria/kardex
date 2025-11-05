"""
Script de Instalación Completo - Sistema Kardex Valorizado
Configura todo el entorno desde cero
"""

import os
import sys
import subprocess
from pathlib import Path

class InstaladorKardex:
    def __init__(self):
        self.directorio_proyecto = Path.cwd()
        self.errores = []
        
    def imprimir_encabezado(self, texto):
        print("\n" + "=" * 70)
        print(f"  {texto}")
        print("=" * 70)
    
    def verificar_python(self):
        """Verifica que Python 3.11+ esté instalado"""
        self.imprimir_encabezado("1. VERIFICANDO PYTHON")
        
        version = sys.version_info
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} detectado")
        
        if version.major < 3 or (version.major == 3 and version.minor < 11):
            print("❌ ERROR: Se requiere Python 3.11 o superior")
            print("   Descarga desde: https://www.python.org/downloads/")
            self.errores.append("Python version incorrecta")
            return False
        
        print("✓ Versión de Python correcta")
        return True
    
    def crear_estructura_directorios(self):
        """Crea la estructura de carpetas del proyecto"""
        self.imprimir_encabezado("2. CREANDO ESTRUCTURA DE DIRECTORIOS")
        
        directorios = [
            "src",
            "src/models",
            "src/controllers",
            "src/views",
            "src/utils",
            "data",
            "backups",
            "temp",
            "exports",
            "plantillas",
            "logs",
            "config"
        ]
        
        for directorio in directorios:
            ruta = self.directorio_proyecto / directorio
            ruta.mkdir(exist_ok=True)
            print(f"✓ Creado: {directorio}/")
        
        # Crear archivos __init__.py
        for directorio in ["src", "src/models", "src/controllers", "src/views", "src/utils"]:
            init_file = self.directorio_proyecto / directorio / "__init__.py"
            init_file.touch(exist_ok=True)
        
        print("✓ Estructura de directorios lista")
        return True
    
    def crear_requirements(self):
        """Crea archivo requirements.txt con todas las dependencias"""
        self.imprimir_encabezado("3. CREANDO REQUIREMENTS.TXT")
        
        requirements = """# Framework GUI
PyQt6==6.6.1
PyQt6-Qt6==6.6.1

# Base de datos
SQLAlchemy==2.0.23
alembic==1.13.1

# Procesamiento de datos
pandas==2.1.4
openpyxl==3.1.2
xlsxwriter==3.1.9

# Reportes PDF
reportlab==4.0.8

# Gráficos
matplotlib==3.8.2
plotly==5.18.0

# OneDrive SDK
onedrivesdk==1.1.8
requests==2.31.0

# Seguridad
cryptography==41.0.7
werkzeug==3.0.1

# Utilidades
python-dotenv==1.0.0
python-dateutil==2.8.2

# Testing
pytest==7.4.3
pytest-qt==4.2.0
"""
        
        requirements_file = self.directorio_proyecto / "requirements.txt"
        requirements_file.write_text(requirements)
        print("✓ requirements.txt creado")
        return True
    
    def instalar_dependencias(self):
        """Instala todas las dependencias de Python"""
        self.imprimir_encabezado("4. INSTALANDO DEPENDENCIAS")
        
        print("Esto puede tomar varios minutos...")
        print("Instalando paquetes con pip...")
        
        try:
            subprocess.check_call([
                sys.executable, 
                "-m", 
                "pip", 
                "install", 
                "-r", 
                "requirements.txt",
                "--upgrade"
            ])
            print("✓ Dependencias instaladas correctamente")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error al instalar dependencias: {e}")
            self.errores.append("Error en instalación de dependencias")
            return False
    
    def crear_archivo_config(self):
        """Crea archivo de configuración .env"""
        self.imprimir_encabezado("5. CREANDO ARCHIVO DE CONFIGURACIÓN")
        
        config = """# Configuración Sistema Kardex Valorizado

# Base de datos
DB_PATH=data/kardex.db

# OneDrive
ONEDRIVE_CLIENT_ID=tu_client_id_aqui
ONEDRIVE_CLIENT_SECRET=tu_client_secret_aqui
ONEDRIVE_FOLDER=KardexValorizado

# Backup
BACKUP_DIR=backups
MAX_BACKUPS=10
BACKUP_AUTO_HORA=23:00

# Licencia
LICENCIA_KEY_FILE=config/licencia.key

# Aplicación
APP_NAME=Kardex Valorizado
APP_VERSION=1.0.0
DEBUG_MODE=False

# IGV
IGV_PORCENTAJE=18.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/kardex.log
"""
        
        env_file = self.directorio_proyecto / ".env"
        env_file.write_text(config)
        print("✓ Archivo .env creado")
        print("⚠️  IMPORTANTE: Edita .env con tus credenciales de OneDrive")
        return True
    
    def crear_gitignore(self):
        """Crea archivo .gitignore"""
        self.imprimir_encabezado("6. CREANDO .GITIGNORE")
        
        gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
dist/
*.egg-info/

# Base de datos
*.db
*.sqlite
*.sqlite3

# Archivos sensibles
.env
config/licencia.key
config/*.key

# Backups
backups/
temp/

# Logs
logs/
*.log

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OneDrive
.onedrive/

# Exportaciones temporales
exports/*.xlsx
exports/*.pdf
"""
        
        gitignore_file = self.directorio_proyecto / ".gitignore"
        gitignore_file.write_text(gitignore)
        print("✓ .gitignore creado")
        return True
    
    def copiar_modelos(self):
        """Copia el modelo de base de datos al proyecto"""
        self.imprimir_encabezado("7. CONFIGURANDO MODELOS")
        
        print("📝 Debes copiar manualmente el archivo 'database_model.py'")
        print("   al directorio: src/models/")
        print("   (El código ya está en el artefact 'database_model')")
        return True
    
    def crear_main(self):
        """Crea archivo main.py inicial"""
        self.imprimir_encabezado("8. CREANDO APLICACIÓN PRINCIPAL")
        
        main_code = """#!/usr/bin/env python3
\"\"\"
Sistema Kardex Valorizado - Aplicación Principal
\"\"\"

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import Qt

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

class KardexMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Sistema Kardex Valorizado")
        self.setGeometry(100, 100, 1200, 800)
        
        # Por ahora, mensaje de bienvenida
        QMessageBox.information(
            self,
            "Bienvenido",
            "Sistema Kardex Valorizado\\n\\nConfiguración inicial completada.\\n\\nPróximos pasos:\\n- Configurar OneDrive\\n- Importar datos iniciales\\n- Crear primera empresa"
        )

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Estilo moderno
    
    ventana = KardexMainWindow()
    ventana.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
"""
        
        main_file = self.directorio_proyecto / "main.py"
        main_file.write_text(main_code)
        print("✓ main.py creado")
        return True
    
    def inicializar_base_datos(self):
        """Inicializa la base de datos"""
        self.imprimir_encabezado("9. INICIALIZANDO BASE DE DATOS")
        
        print("📝 Para inicializar la base de datos:")
        print("   1. Asegúrate de tener database_model.py en src/models/")
        print("   2. Ejecuta: python -c \"from src.models.database_model import crear_base_datos; crear_base_datos('data/kardex.db')\"")
        print("")
        print("   O simplemente ejecuta database_model.py directamente")
        return True
    
    def crear_readme(self):
        """Crea archivo README.md"""
        self.imprimir_encabezado("10. CREANDO DOCUMENTACIÓN")
        
        readme = """# Sistema Kardex Valorizado

Sistema de gestión de inventarios con valorización PEPS/UEPS/Promedio Ponderado.

## Características

- ✅ Gestión de productos con lotes y series
- ✅ Compras con manejo de IGV bimoneda
- ✅ Órdenes de compra
- ✅ Requisiciones y salidas
- ✅ Kardex valorizado con 3 métodos
- ✅ Múltiples empresas y almacenes
- ✅ Importaciones masivas desde Excel
- ✅ Backup automático
- ✅ Sistema de licenciamiento
- ✅ Auditoría completa
- ✅ Sincronización OneDrive multiusuario

## Requisitos

- Python 3.11+
- Windows 10/11
- Conexión a Internet (para OneDrive)
- Office 365 o cuenta Microsoft

## Instalación

1. Clona el repositorio
2. Ejecuta el instalador: `python install_script.py`
3. Edita `.env` con tus credenciales
4. Ejecuta: `python main.py`

## Uso

### Primer uso:
1. Usuario: `admin`
2. Password: `admin123`
3. Cambiar contraseña en primer acceso

### Importar datos:
- Usa las plantillas en `plantillas/`
- Tipo de cambio, proveedores, productos
- Stock inicial por empresa

## Soporte

Para más información consulta la documentación en `docs/`

## Licencia

Propiedad privada. Todos los derechos reservados.
"""
        
        readme_file = self.directorio_proyecto / "README.md"
        readme_file.write_text(readme)
        print("✓ README.md creado")
        return True
    
    def ejecutar_instalacion(self):
        """Ejecuta todo el proceso de instalación"""
        print("\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 15 + "INSTALADOR SISTEMA KARDEX VALORIZADO" + " " * 17 + "║")
        print("╚" + "═" * 68 + "╝")
        
        pasos = [
            self.verificar_python,
            self.crear_estructura_directorios,
            self.crear_requirements,
            self.instalar_dependencias,
            self.crear_archivo_config,
            self.crear_gitignore,
            self.copiar_modelos,
            self.crear_main,
            self.inicializar_base_datos,
            self.crear_readme
        ]
        
        for paso in pasos:
            if not paso():
                print(f"\n❌ Error en paso: {paso.__name__}")
                break
        
        # Resumen final
        self.imprimir_encabezado("INSTALACIÓN COMPLETADA")
        
        if self.errores:
            print("\n⚠️  Se encontraron algunos errores:")
            for error in self.errores:
                print(f"   - {error}")
        else:
            print("\n✅ ¡Instalación exitosa!")
        
        print("\n📋 PRÓXIMOS PASOS:")
        print("   1. Copia database_model.py a src/models/")
        print("   2. Edita .env con tus credenciales de OneDrive")
        print("   3. Ejecuta: python -m src.models.database_model")
        print("   4. Ejecuta: python main.py")
        print("")
        print("📚 Consulta README.md para más información")
        print("")
        print("🎉 ¡Todo listo para empezar a desarrollar!")
        print("")

if __name__ == "__main__":
    instalador = InstaladorKardex()
    instalador.ejecutar_instalacion()
