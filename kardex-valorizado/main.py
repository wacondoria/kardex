#!/usr/bin/env python3
"""
Sistema Kardex Valorizado - Aplicación Principal
Archivo: main.py
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout,
                             QWidget, QMenuBar, QMenu, QToolBar, QPushButton, QTabWidget, QTabBar, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from views.login_window import LoginWindow
from utils.app_context import app_context
from views.productos_window import ProductosWindow
from views.proveedores_window import ProveedoresWindow
from views.clientes_window import ClientesWindow
from views.empresas_window import EmpresasWindow
from views.tipo_cambio_window import TipoCambioWindow
from views.compras_window import ComprasWindow
from views.ventas_window import VentasWindow
from views.kardex_window import KardexWindow
from views.backup_window import BackupWindow
from views.motivos_ajuste_window import MotivosAjusteWindow
from views.ajustes_inventario_window import AjustesInventarioWindow
from views.requisiciones_window import RequisicionesWindow
from views.ordenes_compra_window import OrdenesCompraWindow
from views.seguridad_window import SeguridadWindow
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

    # 6. Verificar nuevas tablas del módulo de Ventas
    try:
        from models.database_model import Cliente, Venta, VentaDetalle, SerieCorrelativo
        tablas_ventas = {
            'clientes': Cliente,
            'ventas': Venta,
            'venta_detalles': VentaDetalle,
            'serie_correlativos': SerieCorrelativo
        }
        for nombre_tabla, modelo_tabla in tablas_ventas.items():
            if not inspector.has_table(nombre_tabla):
                print(f"⚠️  Tabla '{nombre_tabla}' del módulo de ventas no encontrada. Creándola...")
                modelo_tabla.__table__.create(engine)
                print(f"✓  Tabla '{nombre_tabla}' creada exitosamente.")
    except Exception as e:
        print(f"❌ Error al crear las tablas del módulo de ventas: {e}")

    # 7. Verificar columna 'cliente_id' en 'movimientos_stock'
    try:
        columns = [col['name'] for col in inspector.get_columns('movimientos_stock')]
        if 'cliente_id' not in columns:
            print("⚠️  Detectado modelo de 'movimientos_stock' antiguo. Actualizando BD...")
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE movimientos_stock ADD COLUMN cliente_id INTEGER REFERENCES clientes(id)"))
                connection.commit()
            print("✓  Columna 'cliente_id' añadida a 'movimientos_stock' exitosamente.")
    except Exception as e:
        print(f"🔷 Info: Tabla 'movimientos_stock' probablemente no existe aún. Se creará más tarde. ({e})")

    # 8. Verificar nuevas tablas del módulo de Ajustes de Inventario
    try:
        from models.database_model import MotivoAjuste, AjusteInventario, AjusteInventarioDetalle
        tablas_ajustes = {
            'motivos_ajuste': MotivoAjuste,
            'ajustes_inventario': AjusteInventario,
            'ajuste_inventario_detalles': AjusteInventarioDetalle
        }
        for nombre_tabla, modelo_tabla in tablas_ajustes.items():
            if not inspector.has_table(nombre_tabla):
                print(f"⚠️  Tabla '{nombre_tabla}' del módulo de ajustes no encontrada. Creándola...")
                modelo_tabla.__table__.create(engine)
                print(f"✓  Tabla '{nombre_tabla}' creada exitosamente.")
    except Exception as e:
        print(f"❌ Error al crear las tablas del módulo de ajustes: {e}")

    # 9. Verificar columna 'motivo_ajuste_id' en 'movimientos_stock'
    try:
        columns = [col['name'] for col in inspector.get_columns('movimientos_stock')]
        if 'motivo_ajuste_id' not in columns:
            print("⚠️  Detectado modelo de 'movimientos_stock' antiguo. Actualizando BD...")
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE movimientos_stock ADD COLUMN motivo_ajuste_id INTEGER REFERENCES motivos_ajuste(id)"))
                connection.commit()
            print("✓  Columna 'motivo_ajuste_id' añadida a 'movimientos_stock' exitosamente.")
    except Exception as e:
        print(f"🔷 Info: Tabla 'movimientos_stock' probablemente no existe aún. Se creará más tarde. ({e})")

    # 10. Verificar nuevas tablas del sistema de Roles y Permisos
    try:
        from models.database_model import Rol, Permiso, rol_permisos
        tablas_roles = {
            'roles': Rol,
            'permisos': Permiso
        }
        for nombre_tabla, modelo_tabla in tablas_roles.items():
            if not inspector.has_table(nombre_tabla):
                print(f"⚠️  Tabla '{nombre_tabla}' del sistema de roles no encontrada. Creándola...")
                modelo_tabla.__table__.create(engine)
                print(f"✓  Tabla '{nombre_tabla}' creada exitosamente.")

        if not inspector.has_table('rol_permisos'):
            print(f"⚠️  Tabla de asociación 'rol_permisos' no encontrada. Creándola...")
            rol_permisos.create(engine)
            print(f"✓  Tabla 'rol_permisos' creada exitosamente.")

    except Exception as e:
        print(f"❌ Error al crear las tablas del sistema de roles: {e}")

    # 11. Verificar columna 'rol_id' en 'usuarios'
    try:
        columns = [col['name'] for col in inspector.get_columns('usuarios')]
        if 'rol_id' not in columns:
            print("⚠️  Detectado modelo de 'usuarios' antiguo. Actualizando BD...")
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN rol_id INTEGER REFERENCES roles(id)"))
                connection.commit()
            print("✓  Columna 'rol_id' añadida a 'usuarios' exitosamente.")
    except Exception as e:
        print(f"🔷 Info: Tabla 'usuarios' probablemente no existe aún. Se creará más tarde. ({e})")

    # 12. Lógica de Siembra y Migración de Datos
    try:
        from models.database_model import usuario_empresa, Usuario, Empresa

        # Asegurar que la tabla de asociación 'usuario_empresa' exista
        if not inspector.has_table('usuario_empresa'):
            print("⚠️  Tabla 'usuario_empresa' no encontrada. Creándola...")
            usuario_empresa.create(engine)
            print("✓  Tabla 'usuario_empresa' creada.")

        # Realizar siembra y migración en una sesión para garantizar consistencia
        with sessionmaker(bind=engine)() as session:
            # Paso 1: Asegurar que exista al menos una empresa (para instalaciones nuevas)
            if session.query(Empresa).count() == 0:
                print("⚠️  No hay empresas en la BD. Creando una por defecto...")
                empresa_default = Empresa(
                    ruc="12345678901",
                    razon_social="MI EMPRESA (EDITAR DATOS)",
                    direccion="DIRECCION DE MI EMPRESA",
                    activo=True
                )
                session.add(empresa_default)
                session.commit()
                print("✓  Empresa por defecto creada.")

            # Paso 2: Asegurar que el usuario admin esté vinculado a una empresa
            admin_user = session.query(Usuario).filter_by(username='admin').first()
            if admin_user and not admin_user.empresas:
                print("⚠️  Usuario 'admin' no tiene empresa. Asignando la primera disponible...")
                primera_empresa = session.query(Empresa).first()
                if primera_empresa:
                    admin_user.empresas.append(primera_empresa)
                    session.commit()
                    print(f"✓  Usuario 'admin' asignado a '{primera_empresa.razon_social}'.")
                else:
                    # Este caso no debería ocurrir gracias al Paso 1, pero se incluye por seguridad
                    print("❌ Error Crítico: No hay empresas para asignar al admin.")
            elif admin_user:
                print("👍  Usuario 'admin' ya tiene empresa asignada.")

    except Exception as e:
        print(f"❌ Error durante la siembra y migración de datos: {e}")


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
        self.ventana_clientes = None
        self.ventana_empresas = None
        self.ventana_tipo_cambio = None
        self.ventana_compras = None
        self.ventana_ventas = None
        self.ventana_kardex = None
        self.ventana_backup = None
        self.ventana_seguridad = None
        self.ventana_usuarios = None
        self.ventana_admin_roles = None
        self.ventana_valorizacion = None
        self.ventana_requisiciones = None
        self.ventana_ordenes_compra = None
        self.ventana_admin_anios = None
        self.ventana_importacion = None
        self.ventana_motivos_ajuste = None
        self.ventana_ajustes_inventario = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Sistema Kardex Valorizado - {self.user_info['nombre_completo']} | Año: {self.selected_year}")
        self.showMaximized()

        # Crear menú
        self.crear_menu()

        # Crear toolbar
        self.crear_toolbar()

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.cerrar_pestana)
        self.setCentralWidget(self.tab_widget)

        # Crear pestaña de bienvenida
        self.crear_pestana_bienvenida()

    def crear_pestana_bienvenida(self):
        """Crea la pestaña de bienvenida inicial"""
        bienvenida_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
            "\n\n📋 Para comenzar, selecciona una opción del menú o la barra de herramientas."
        )
        instrucciones.setFont(QFont("Arial", 11))
        instrucciones.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instrucciones.setStyleSheet("color: #666;")

        layout.addWidget(bienvenida)
        layout.addWidget(info)
        layout.addWidget(instrucciones)

        bienvenida_widget.setLayout(layout)

        index = self.tab_widget.addTab(bienvenida_widget, "🏠 Inicio")
        self.tab_widget.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, None)

    def cerrar_pestana(self, index):
        """Cierra una pestaña del tab widget"""
        widget = self.tab_widget.widget(index)
        if widget is not None:
            widget.deleteLater()
        self.tab_widget.removeTab(index)

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

        accion_clientes = QAction("👤 Clientes", self)
        accion_clientes.triggered.connect(self.abrir_clientes)
        menu_maestros.addAction(accion_clientes)

        accion_empresas = QAction("🏢 Empresas y Almacenes", self)
        accion_empresas.setShortcut("Ctrl+E")
        accion_empresas.triggered.connect(self.abrir_empresas)
        accion_empresas.setEnabled(app_context.has_permission('configuracion_sistema'))
        menu_maestros.addAction(accion_empresas)

        menu_maestros.addSeparator()

        accion_tipo_cambio = QAction("💱 Tipo de Cambio", self)
        accion_tipo_cambio.setShortcut("Ctrl+T")
        accion_tipo_cambio.triggered.connect(self.abrir_tipo_cambio)
        menu_maestros.addAction(accion_tipo_cambio)

        accion_motivos_ajuste = QAction("📝 Motivos de Ajuste", self)
        accion_motivos_ajuste.triggered.connect(self.abrir_motivos_ajuste)
        menu_maestros.addAction(accion_motivos_ajuste)

        # Menú Operaciones
        menu_operaciones = menubar.addMenu("📊 Operaciones")

        accion_compras = QAction("🛒 Compras", self)
        accion_compras.setShortcut("Ctrl+C")
        accion_compras.triggered.connect(self.abrir_compras)
        menu_operaciones.addAction(accion_compras)

        accion_ventas = QAction("📦 Ventas", self)
        accion_ventas.triggered.connect(self.abrir_ventas)
        menu_operaciones.addAction(accion_ventas)

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

        accion_ajustes = QAction("⚙️ Ajuste de Inventario", self)
        accion_ajustes.triggered.connect(self.abrir_ajustes_inventario)
        menu_operaciones.addAction(accion_ajustes)

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

        accion_seguridad = QAction("🔐 Seguridad (Usuarios y Roles)", self)
        accion_seguridad.setEnabled(app_context.has_permission('gestionar_usuarios'))
        accion_seguridad.triggered.connect(self.abrir_seguridad)
        menu_sistema.addAction(accion_seguridad)

        accion_admin_anios = QAction("🗓️ Administración de Años", self)
        accion_admin_anios.setEnabled(app_context.has_permission('configuracion_sistema'))
        accion_admin_anios.triggered.connect(self.abrir_admin_anios)
        menu_sistema.addAction(accion_admin_anios)

        accion_importacion = QAction("⬆️ Central de Importaciones", self)
        accion_importacion.setEnabled(app_context.has_permission('configuracion_sistema'))
        accion_importacion.triggered.connect(self.abrir_importacion)
        menu_sistema.addAction(accion_importacion)

        menu_sistema.addSeparator()

        accion_backup = QAction("💾 Backup/Restore", self)
        accion_backup.setEnabled(app_context.has_permission('configuracion_sistema'))
        accion_backup.triggered.connect(self.abrir_backup)
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

        btn_compras = QPushButton("🛒 Compras")
        btn_compras.clicked.connect(self.abrir_compras)
        toolbar.addWidget(btn_compras)

        btn_ventas = QPushButton("📦 Ventas")
        btn_ventas.clicked.connect(self.abrir_ventas)
        toolbar.addWidget(btn_ventas)

        btn_ordenes_compra = QPushButton("📄 Órdenes de Compra")
        btn_ordenes_compra.clicked.connect(self.abrir_ordenes_compra)
        toolbar.addWidget(btn_ordenes_compra)

        # --- 3. CORRECCIÓN EN LA BARRA DE HERRAMIENTAS ---
        btn_requisiciones = QPushButton("📤 Requisiciones")
        # Se elimina la línea: btn_requisiciones.setEnabled(False)
        # Y se añade la siguiente para que se conecte y funcione:
        btn_requisiciones.clicked.connect(self.abrir_requisiciones)
        toolbar.addWidget(btn_requisiciones)

        btn_ajustes = QPushButton("⚙️ Ajustes")
        btn_ajustes.clicked.connect(self.abrir_ajustes_inventario)
        toolbar.addWidget(btn_ajustes)

        toolbar.addSeparator()

        btn_kardex = QPushButton("📊 Kardex")
        btn_kardex.clicked.connect(self.abrir_kardex)
        toolbar.addWidget(btn_kardex)

        btn_valorizacion = QPushButton("💰 Valorización")
        btn_valorizacion.clicked.connect(self.abrir_valorizacion)
        toolbar.addWidget(btn_valorizacion)

        toolbar.addSeparator()

    def abrir_productos(self):
        """Abre la ventana de gestión de productos en una nueva pestaña"""
        nombre_pestana = "Productos"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return

        productos_widget = ProductosWindow()
        self.tab_widget.addTab(productos_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(productos_widget)

    def abrir_kardex(self):
        """Abre la ventana de Kardex Valorizado en una nueva pestaña"""
        nombre_pestana = "Kardex"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return

        kardex_widget = KardexWindow()
        self.tab_widget.addTab(kardex_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(kardex_widget)

    def abrir_compras(self):
        """Abre la ventana de gestión de compras en una nueva pestaña"""
        nombre_pestana = "Compras"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return

        compras_widget = ComprasWindow(self.user_info)
        self.tab_widget.addTab(compras_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(compras_widget)

    def abrir_ventas(self):
        """Abre la ventana de gestión de ventas en una nueva pestaña"""
        nombre_pestana = "Ventas"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return

        ventas_widget = VentasWindow(self.user_info)
        self.tab_widget.addTab(ventas_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(ventas_widget)

    def abrir_tipo_cambio(self):
        """Abre la ventana de gestión de tipo de cambio"""
        if self.ventana_tipo_cambio is None:
            self.ventana_tipo_cambio = TipoCambioWindow()

        self.ventana_tipo_cambio.show()
        self.ventana_tipo_cambio.raise_()
        self.ventana_tipo_cambio.activateWindow()

    def abrir_empresas(self):
        """Abre la ventana de gestión de empresas"""
        if not app_context.has_permission('configuracion_sistema'):
            QMessageBox.warning(self, "Acceso Denegado", "No tienes permiso para gestionar empresas.")
            return

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

    def abrir_clientes(self):
        """Abre la ventana de gestión de clientes"""
        if self.ventana_clientes is None:
            self.ventana_clientes = ClientesWindow()

        self.ventana_clientes.show()
        self.ventana_clientes.raise_()
        self.ventana_clientes.activateWindow()

    def abrir_backup(self):
        """Abre la ventana de backup"""
        if not app_context.has_permission('configuracion_sistema'):
            QMessageBox.warning(self, "Acceso Denegado", "No tienes permiso para gestionar backups.")
            return

        if not hasattr(self, 'ventana_backup') or self.ventana_backup is None:
            self.ventana_backup = BackupWindow()

        self.ventana_backup.show()
        self.ventana_backup.raise_()
        self.ventana_backup.activateWindow()

    def abrir_requisiciones(self):
        """Abre la ventana de gestión de requisiciones en una nueva pestaña"""
        nombre_pestana = "Requisiciones"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return

        requisiciones_widget = RequisicionesWindow(user_info=self.user_info)
        self.tab_widget.addTab(requisiciones_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(requisiciones_widget)

    def abrir_ordenes_compra(self):
        """Abre la ventana de gestión de órdenes de compra en una nueva pestaña"""
        nombre_pestana = "Órdenes de Compra"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return

        ordenes_compra_widget = OrdenesCompraWindow(self.user_info)
        self.tab_widget.addTab(ordenes_compra_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(ordenes_compra_widget)

    def abrir_seguridad(self):
        """Abre la ventana de gestión de seguridad (usuarios y roles)"""
        if not app_context.has_permission('gestionar_usuarios'):
            QMessageBox.warning(self, "Acceso Denegado", "No tienes permiso para gestionar la seguridad.")
            return

        if self.ventana_seguridad is None:
            self.ventana_seguridad = SeguridadWindow()

        self.ventana_seguridad.show()
        self.ventana_seguridad.raise_()
        self.ventana_seguridad.activateWindow()

    def abrir_valorizacion(self):
        """Abre la ventana de valorización de inventario en una nueva pestaña"""
        nombre_pestana = "Valorización"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return

        valorizacion_widget = ValorizacionWindow()
        self.tab_widget.addTab(valorizacion_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(valorizacion_widget)

    def abrir_admin_anios(self):
        """Abre la ventana de administración de años contables."""
        if not app_context.has_permission('configuracion_sistema'):
            QMessageBox.warning(self, "Acceso Denegado", "No tienes permiso para gestionar los años contables.")
            return

        if self.ventana_admin_anios is None:
            self.ventana_admin_anios = AnioContableWindow()

        self.ventana_admin_anios.show()
        self.ventana_admin_anios.raise_()
        self.ventana_admin_anios.activateWindow()

    def abrir_importacion(self):
        """Abre la ventana de importación de datos."""
        if not app_context.has_permission('configuracion_sistema'):
            QMessageBox.warning(self, "Acceso Denegado", "No tienes permiso para importar datos.")
            return

        if self.ventana_importacion is None:
            self.ventana_importacion = SistemasImportacionWindow()

        self.ventana_importacion.show()
        self.ventana_importacion.raise_()
        self.ventana_importacion.activateWindow()

    def abrir_motivos_ajuste(self):
        """Abre la ventana de gestión de motivos de ajuste."""
        if self.ventana_motivos_ajuste is None:
            self.ventana_motivos_ajuste = MotivosAjusteWindow()

        self.ventana_motivos_ajuste.show()
        self.ventana_motivos_ajuste.raise_()
        self.ventana_motivos_ajuste.activateWindow()

    def abrir_ajustes_inventario(self):
        """Abre la ventana de gestión de ajustes de inventario en una nueva pestaña."""
        nombre_pestana = "Ajustes de Inventario"
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == nombre_pestana:
                self.tab_widget.setCurrentIndex(i)
                return

        ajustes_widget = AjustesInventarioWindow(self.user_info)
        self.tab_widget.addTab(ajustes_widget, nombre_pestana)
        self.tab_widget.setCurrentWidget(ajustes_widget)


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
