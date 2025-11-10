#!/usr/bin/env python3
"""
Sistema Kardex Valorizado - Aplicación Principal
Archivo: main.py
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout,
                             QWidget, QMenuBar, QMenu, QToolBar, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from views.login_window import LoginWindow
from utils.app_context import app_context
from views.productos_window import ProductosWindow
from views.proveedores_window import ProveedoresWindow
from views.empresas_window import EmpresasWindow
from views.tipo_cambio_window import TipoCambioWindow
from views.compras_window import ComprasWindow
from views.kardex_window import KardexWindow
from views.backup_window import BackupWindow
from views.requisiciones_window import RequisicionesWindow
from views.ordenes_compra_window import OrdenesCompraWindow
from views.usuarios_window import UsuariosWindow
from views.valorizacion_window import ValorizacionWindow
from views.anio_contable_window import AnioContableWindow
from views.sistemas_importacion_window import SistemasImportacionWindow

# --- Integración para actualización automática ---
from utils.actualizador_tc import actualizar_tc_desde_excel
from models.database_model import obtener_session
from utils.themes import get_theme_stylesheet

# --- MODIFICADO: Añadida función de migración de BD ---
from sqlalchemy import create_engine, inspect, text
from models.database_model import AnioContable, EstadoAnio, Compra
from datetime import datetime
from collections import defaultdict

def verificar_y_actualizar_db(db_url='sqlite:///kardex.db'):
    """
    Verifica y actualiza la estructura de la base de datos.
    - Añade la columna 'activo' a 'tipo_cambio' si no existe.
    - Crea la tabla 'anio_contable' si no existe.
    - Inserta el año actual si la tabla de años está vacía.
    """
    engine = create_engine(db_url)
    inspector = inspect(engine)

    # 1. Verificar columna 'activo' en 'tipo_cambio'
    try:
        columns = [col['name'] for col in inspector.get_columns('tipo_cambio')]
        if 'activo' not in columns:
            print("⚠️  Detectado modelo de 'tipo_cambio' antiguo. Actualizando BD...")
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE tipo_cambio ADD COLUMN activo BOOLEAN DEFAULT 1 NOT NULL"))
                connection.commit()
            print("✓  Columna 'activo' añadida a 'tipo_cambio' exitosamente.")
    except Exception as e:
        print(f"🔷 Info: Tabla 'tipo_cambio' probablemente no existe aún. Se creará más tarde. ({e})")

    # 2. Verificar y crear la tabla 'anio_contable'
    if not inspector.has_table('anio_contable'):
        print("⚠️  Tabla 'anio_contable' no encontrada. Creándola...")
        try:
            AnioContable.__table__.create(engine)
            print("✓  Tabla 'anio_contable' creada exitosamente.")

            with sessionmaker(bind=engine)() as session:
                print("🗓️  Poblando la tabla 'anio_contable' con el año actual...")
                anio_actual = AnioContable(
                    anio=datetime.now().year,
                    estado=EstadoAnio.ABIERTO
                )
                session.add(anio_actual)
                session.commit()
                print(f"✓  Año {datetime.now().year} añadido como 'Abierto'.")

        except Exception as e:
            print(f"❌  Error al crear o poblar la tabla 'anio_contable': {e}")
    else:
        # 3. Si la tabla ya existe, verificar que haya al menos un año abierto
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        with Session() as session:
            anios_abiertos = session.query(AnioContable).filter_by(estado=EstadoAnio.ABIERTO).count()
            if anios_abiertos == 0:
                print("⚠️  No se encontraron años contables abiertos. Creando año 2025...")

                anio_2025_existe = session.query(AnioContable).filter_by(anio=2025).count() > 0

                if anio_2025_existe:
                    print("↪️  El año 2025 ya existe. Cambiando su estado a 'Abierto'.")
                    session.query(AnioContable).filter_by(anio=2025).update({'estado': EstadoAnio.ABIERTO})
                else:
                    nuevo_anio = AnioContable(anio=2025, estado=EstadoAnio.ABIERTO)
                    session.add(nuevo_anio)
                    print("✓  Año 2025 creado como 'Abierto'.")

                session.commit()

    # 4. Verificar columna 'es_principal' en 'almacenes' y eliminarla de 'empresas'
    try:
        # Añadir a 'almacenes' si no existe
        columns_almacenes = [col['name'] for col in inspector.get_columns('almacenes')]
        if 'es_principal' not in columns_almacenes:
            print("⚠️  Detectado modelo de 'almacenes' antiguo. Actualizando BD...")
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE almacenes ADD COLUMN es_principal BOOLEAN DEFAULT 0 NOT NULL"))
                connection.commit()
            print("✓  Columna 'es_principal' añadida a 'almacenes' exitosamente.")

        # Eliminar de 'empresas' si existe (para corregir errores pasados)
        columns_empresas = [col['name'] for col in inspector.get_columns('empresas')]
        if 'es_principal' in columns_empresas:
            print("⚠️  Detectada columna 'es_principal' obsoleta en 'empresas'. Eliminándola...")
            with engine.connect() as connection:
                # SQLite no soporta DROP COLUMN directamente en todas las versiones
                # de forma segura. Se utiliza un método de recreación de tabla.
                connection.execute(text("CREATE TABLE empresas_new AS SELECT id, ruc, razon_social, direccion, telefono, email, metodo_valuacion, activo, fecha_registro FROM empresas"))
                connection.execute(text("DROP TABLE empresas"))
                connection.execute(text("ALTER TABLE empresas_new RENAME TO empresas"))
                connection.commit()
            print("✓  Columna 'es_principal' eliminada de 'empresas' exitosamente.")

    except Exception as e:
        print(f"🔷 Info: Tabla 'almacenes' o 'empresas' probablemente no existe aún. Se creará más tarde. ({e})")

    # 5. Verificar columna 'numero_proceso' en 'compras'
    try:
        columns = [col['name'] for col in inspector.get_columns('compras')]
        if 'numero_proceso' not in columns:
            print("⚠️  Detectado modelo de 'compras' antiguo. Actualizando BD...")
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE compras ADD COLUMN numero_proceso VARCHAR(20)"))
                connection.commit()
            print("✓  Columna 'numero_proceso' añadida a 'compras' exitosamente.")

            # Poblar 'numero_proceso' para datos existentes
            print("ℹ️  Asignando 'numero_proceso' a compras existentes...")
            with sessionmaker(bind=engine)() as session:
                compras_sin_proceso = session.query(Compra).filter(Compra.numero_proceso == None).order_by(Compra.fecha_registro_contable, Compra.id).all()

                if compras_sin_proceso:
                    correlativos = defaultdict(int)
                    for compra in compras_sin_proceso:
                        # Usar fecha_registro_contable si existe, si no, la fecha de emisión
                        fecha = compra.fecha_registro_contable or compra.fecha
                        if fecha:
                            mes = f"{fecha.month:02d}"
                            correlativos[mes] += 1
                            correlativo_actual = correlativos[mes]
                            compra.numero_proceso = f"06{mes}{correlativo_actual:06d}"
                        else:
                            # Caso fallback si no hay ninguna fecha
                            compra.numero_proceso = f"0600000000"

                    session.commit()
                    print(f"✓  Se actualizaron {len(compras_sin_proceso)} compras existentes.")
                else:
                    print("👍 No hay compras existentes que necesiten actualización.")
    except Exception as e:
        print(f"🔷 Info: Tabla 'compras' probablemente no existe aún. Se creará más tarde. ({e})")

class KardexMainWindow(QMainWindow):
    """Ventana principal del sistema"""

    def __init__(self):
        super().__init__()
        # Cargar datos desde el contexto global
        self.user_info = app_context.get_user_info()
        self.selected_year = app_context.get_selected_year()

        # Guardar referencia en el contexto para acceso global
        app_context.set_main_window(self)

        self.ventana_productos = None
        self.ventana_proveedores = None
        self.ventana_empresas = None
        self.ventana_tipo_cambio = None
        self.ventana_compras = None
        self.ventana_kardex = None
        self.ventana_backup = None
        self.ventana_usuarios = None
        self.ventana_valorizacion = None
        self.ventana_requisiciones = None
        self.ventana_ordenes_compra = None
        self.ventana_admin_anios = None
        self.ventana_importacion = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Sistema Kardex Valorizado - {self.user_info['nombre_completo']} | Año: {self.selected_year}")
        self.setGeometry(100, 100, 1200, 800)

        # Crear menú
        self.crear_menu()

        # Crear toolbar
        self.crear_toolbar()

        # Widget central temporal
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mensaje de bienvenida
        bienvenida = QLabel(f"🎉 ¡Bienvenido al Sistema!\n\n")
        bienvenida.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        bienvenida.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info = QLabel(
            f"Usuario: {self.user_info['username']}\n"
            f"Nombre: {self.user_info['nombre_completo']}\n"
            f"Rol: {self.user_info['rol']}\n\n"
            f"{'⚠️ MODO SOLO CONSULTA (Licencia vencida)' if self.user_info['licencia_vencida'] else '✅ Sistema operativo'}"
        )
        info.setFont(QFont("Arial", 12))
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        instrucciones = QLabel(
            "\n\n📋 Para comenzar:\n\n"
            "• Menú: Maestros → Productos\n"
            "• O usa el botón de la barra de herramientas"
        )
        instrucciones.setFont(QFont("Arial", 11))
        instrucciones.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instrucciones.setStyleSheet("color: #666;")

        layout.addWidget(bienvenida)
        layout.addWidget(info)
        layout.addWidget(instrucciones)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def crear_menu(self):
        """Crea el menú principal"""
        menubar = self.menuBar()

        # Menú Maestros
        menu_maestros = menubar.addMenu("📋 Maestros")

        accion_productos = QAction("📦 Productos", self)
        accion_productos.setShortcut("Ctrl+P")
        accion_productos.triggered.connect(self.abrir_productos)
        menu_maestros.addAction(accion_productos)

        accion_proveedores = QAction("🏪 Proveedores", self)
        accion_proveedores.setShortcut("Ctrl+R")
        accion_proveedores.triggered.connect(self.abrir_proveedores)
        menu_maestros.addAction(accion_proveedores)

        accion_empresas = QAction("🏢 Empresas y Almacenes", self)
        accion_empresas.setShortcut("Ctrl+E")
        accion_empresas.triggered.connect(self.abrir_empresas)
        accion_empresas.setEnabled(self.user_info['rol'] == 'ADMINISTRADOR')
        menu_maestros.addAction(accion_empresas)

        menu_maestros.addSeparator()

        accion_tipo_cambio = QAction("💱 Tipo de Cambio", self)
        accion_tipo_cambio.setShortcut("Ctrl+T")
        accion_tipo_cambio.triggered.connect(self.abrir_tipo_cambio)
        menu_maestros.addAction(accion_tipo_cambio)

        # Menú Operaciones
        menu_operaciones = menubar.addMenu("📊 Operaciones")

        accion_compras = QAction("🛒 Compras", self)
        accion_compras.setShortcut("Ctrl+C")
        accion_compras.triggered.connect(self.abrir_compras)
        menu_operaciones.addAction(accion_compras)

        accion_ordenes_compra = QAction("📄 Órdenes de Compra", self)
        accion_ordenes_compra.setShortcut("Ctrl+O")
        accion_ordenes_compra.triggered.connect(self.abrir_ordenes_compra)
        menu_operaciones.addAction(accion_ordenes_compra)

        # --- 2. CORRECCIÓN EN EL MENÚ ---
        accion_requisiciones = QAction("📤 Requisiciones", self)
        # Se elimina la línea: accion_requisiciones.setEnabled(False)
        # Y se añaden las siguientes para que se conecte y funcione:
        accion_requisiciones.setShortcut("Ctrl+S") # S de Salida
        accion_requisiciones.triggered.connect(self.abrir_requisiciones)
        menu_operaciones.addAction(accion_requisiciones)

        # Menú Reportes
        menu_reportes = menubar.addMenu("📈 Reportes")

        accion_kardex = QAction("📊 Kardex Valorizado", self)
        accion_kardex.setShortcut("Ctrl+K")
        accion_kardex.triggered.connect(self.abrir_kardex)
        menu_reportes.addAction(accion_kardex)

        accion_inventario = QAction("📋 Valorización Inventario", self)
        accion_inventario.setEnabled(True)
        accion_inventario.triggered.connect(self.abrir_valorizacion)
        menu_reportes.addAction(accion_inventario)

        # Menú Sistema
        menu_sistema = menubar.addMenu("⚙️ Sistema")

        accion_usuarios = QAction("👥 Usuarios", self)
        accion_usuarios.setEnabled(self.user_info['rol'] == 'ADMINISTRADOR')
        accion_usuarios.triggered.connect(self.abrir_usuarios)
        menu_sistema.addAction(accion_usuarios)

        accion_admin_anios = QAction("🗓️ Administración de Años", self)
        accion_admin_anios.setEnabled(self.user_info['rol'] == 'ADMINISTRADOR')
        accion_admin_anios.triggered.connect(self.abrir_admin_anios)
        menu_sistema.addAction(accion_admin_anios)

        accion_importacion = QAction("⬆️ Central de Importaciones", self)
        accion_importacion.triggered.connect(self.abrir_importacion)
        menu_sistema.addAction(accion_importacion)

        menu_sistema.addSeparator()

        accion_backup = QAction("💾 Backup/Restore", self)
        accion_backup.triggered.connect(self.abrir_backup)
        accion_backup.setEnabled(self.user_info['rol'] == 'ADMINISTRADOR')
        menu_sistema.addAction(accion_backup)

        menu_sistema.addSeparator()

        accion_salir = QAction("🚪 Salir", self)
        accion_salir.setShortcut("Ctrl+Q")
        accion_salir.triggered.connect(self.close)
        menu_sistema.addAction(accion_salir)

    def crear_toolbar(self):
        """Crea la barra de herramientas"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Botón Productos
        btn_productos = QPushButton("📦 Productos")
        btn_productos.clicked.connect(self.abrir_productos)
        toolbar.addWidget(btn_productos)

        # Botones deshabilitados por ahora
        btn_proveedores = QPushButton("🏪 Proveedores")
        btn_proveedores.clicked.connect(self.abrir_proveedores)
        toolbar.addWidget(btn_proveedores)

        btn_compras = QPushButton("🛒 Compras")
        btn_compras.clicked.connect(self.abrir_compras)
        toolbar.addWidget(btn_compras)

        btn_ordenes_compra = QPushButton("📄 Órdenes de Compra")
        btn_ordenes_compra.clicked.connect(self.abrir_ordenes_compra)
        toolbar.addWidget(btn_ordenes_compra)

        # --- 3. CORRECCIÓN EN LA BARRA DE HERRAMIENTAS ---
        btn_requisiciones = QPushButton("📤 Requisiciones")
        # Se elimina la línea: btn_requisiciones.setEnabled(False)
        # Y se añade la siguiente para que se conecte y funcione:
        btn_requisiciones.clicked.connect(self.abrir_requisiciones)
        toolbar.addWidget(btn_requisiciones)

        toolbar.addSeparator()

        btn_kardex = QPushButton("📊 Kardex")
        btn_kardex.clicked.connect(self.abrir_kardex)
        toolbar.addWidget(btn_kardex)

        btn_valorizacion = QPushButton("💰 Valorización")
        btn_valorizacion.clicked.connect(self.abrir_valorizacion)
        toolbar.addWidget(btn_valorizacion)

        toolbar.addSeparator()

        btn_usuarios = QPushButton("👥 Usuarios")
        btn_usuarios.clicked.connect(self.abrir_usuarios)
        btn_usuarios.setEnabled(self.user_info['rol'] == 'ADMINISTRADOR')
        toolbar.addWidget(btn_usuarios)

    def abrir_productos(self):
        """Abre la ventana de gestión de productos"""
        if self.ventana_productos is None:
            self.ventana_productos = ProductosWindow()

        self.ventana_productos.show()
        self.ventana_productos.raise_()
        self.ventana_productos.activateWindow()

    def abrir_kardex(self):
        """Abre la ventana de Kardex Valorizado"""
        if self.ventana_kardex is None:
            self.ventana_kardex = KardexWindow()

        self.ventana_kardex.show()
        self.ventana_kardex.raise_()
        self.ventana_kardex.activateWindow()

    def abrir_compras(self):
        """Abre la ventana de gestión de compras"""
        if self.ventana_compras is None:
            self.ventana_compras = ComprasWindow(self.user_info)

        self.ventana_compras.show()
        self.ventana_compras.raise_()
        self.ventana_compras.activateWindow()

    def abrir_tipo_cambio(self):
        """Abre la ventana de gestión de tipo de cambio"""
        if self.ventana_tipo_cambio is None:
            self.ventana_tipo_cambio = TipoCambioWindow()

        self.ventana_tipo_cambio.show()
        self.ventana_tipo_cambio.raise_()
        self.ventana_tipo_cambio.activateWindow()

    def abrir_empresas(self):
        """Abre la ventana de gestión de empresas"""
        if self.ventana_empresas is None:
            self.ventana_empresas = EmpresasWindow()

        self.ventana_empresas.show()
        self.ventana_empresas.raise_()
        self.ventana_empresas.activateWindow()

    def abrir_proveedores(self):
        """Abre la ventana de gestión de proveedores"""
        if self.ventana_proveedores is None:
            self.ventana_proveedores = ProveedoresWindow()

        self.ventana_proveedores.show()
        self.ventana_proveedores.raise_()
        self.ventana_proveedores.activateWindow()

    def abrir_backup(self):
        """Abre la ventana de backup"""
        if not hasattr(self, 'ventana_backup') or self.ventana_backup is None:
            self.ventana_backup = BackupWindow()

        self.ventana_backup.show()
        self.ventana_backup.raise_()
        self.ventana_backup.activateWindow()

    def abrir_requisiciones(self):
        """Abre la ventana de gestión de requisiciones"""
        if self.ventana_requisiciones is None:
            self.ventana_requisiciones = RequisicionesWindow(user_info=self.user_info)

        self.ventana_requisiciones.show()
        self.ventana_requisiciones.raise_()
        self.ventana_requisiciones.activateWindow()

    def abrir_ordenes_compra(self):
        """Abre la ventana de gestión de órdenes de compra"""
        if self.ventana_ordenes_compra is None:
            self.ventana_ordenes_compra = OrdenesCompraWindow(self.user_info)

        self.ventana_ordenes_compra.show()
        self.ventana_ordenes_compra.raise_()
        self.ventana_ordenes_compra.activateWindow()

    def abrir_usuarios(self):
        """Abre la ventana de gestión de usuarios"""
        if self.ventana_usuarios is None:
            self.ventana_usuarios = UsuariosWindow()

        self.ventana_usuarios.show()
        self.ventana_usuarios.raise_()
        self.ventana_usuarios.activateWindow()

    def abrir_valorizacion(self):
        """Abre la ventana de valorización de inventario"""
        if self.ventana_valorizacion is None:
            self.ventana_valorizacion = ValorizacionWindow()

        self.ventana_valorizacion.show()
        self.ventana_valorizacion.raise_()
        self.ventana_valorizacion.activateWindow()

    def abrir_admin_anios(self):
        """Abre la ventana de administración de años contables."""
        if self.ventana_admin_anios is None:
            self.ventana_admin_anios = AnioContableWindow()

        self.ventana_admin_anios.show()
        self.ventana_admin_anios.raise_()
        self.ventana_admin_anios.activateWindow()

    def abrir_importacion(self):
        """Abre la ventana de importación de datos."""
        if self.ventana_importacion is None:
            self.ventana_importacion = SistemasImportacionWindow()

        self.ventana_importacion.show()
        self.ventana_importacion.raise_()
        self.ventana_importacion.activateWindow()


def main():
    verificar_y_actualizar_db()

    session = obtener_session()
    try:
        ruta_excel = r"C:\Users\USER\OneDrive\MIM\DATABASS\BASE DE DATOS.xlsx"
        nombre_hoja = "TCbio"
        actualizar_tc_desde_excel(session, ruta_excel, nombre_hoja)
    except Exception as e:
        print(f"Error durante la actualización de TC: {e}")
    finally:
        session.close()

    app = QApplication(sys.argv)

    # --- CORREGIDO: Uso de ruta absoluta para los recursos ---
    # Determinar la ruta base del proyecto. Si está congelado (PyInstaller),
    # usa el directorio del ejecutable. Si no, usa el directorio padre de `main.py`.
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent

    # Aplicar el tema (claro/oscuro) detectado
    stylesheet = get_theme_stylesheet(base_path=base_path.as_posix())
    app.setStyleSheet(stylesheet)

    main_window = None
    login_window = LoginWindow()

    def on_login_successful(user_info):
        nonlocal main_window
        main_window = KardexMainWindow()
        main_window.show()
        login_window.close()

    login_window.login_exitoso.connect(on_login_successful)
    login_window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
