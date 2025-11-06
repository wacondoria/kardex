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

# --- Integración para actualización automática ---
from utils.actualizador_tc import actualizar_tc_desde_excel
from models.database_model import obtener_session

class KardexMainWindow(QMainWindow):
    """Ventana principal del sistema"""

    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.ventana_productos = None
        self.ventana_proveedores = None
        self.ventana_empresas = None
        self.ventana_tipo_cambio = None
        self.ventana_compras = None
        self.ventana_kardex = None
        self.ventana_backup = None
        self.ventana_usuarios = None
        self.ventana_valorizacion = None
        # --- 1. Variable inicializada (esto ya estaba bien) ---
        self.ventana_requisiciones = None
        self.ventana_ordenes_compra = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Sistema Kardex Valorizado - {self.user_info['nombre_completo']}")
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
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f1f3f4;
                border: none;
                padding: 5px;
                spacing: 5px;
            }
            QPushButton {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e8f0fe;
                border: 1px solid #1a73e8;
            }
        """)
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


def main():
    # --- Actualización automática de TC ---
    session = obtener_session()
    try:
        # La ruta es relativa a main.py, que está en el directorio raíz del proyecto
        ruta_excel = str(Path(__file__).parent / 'plantilla_tipo_cambio.xlsx')
        actualizar_tc_desde_excel(session, ruta_excel, 'Hoja1')
    except Exception as e:
        print(f"Error durante la actualización de TC: {e}")
    finally:
        session.close()
    # --- Fin de la actualización ---

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Mostrar ventana de login
    login = LoginWindow()

    # Variable para guardar la ventana principal
    main_window = None

    def on_login_exitoso(user_info):
        """Callback cuando el login es exitoso"""
        nonlocal main_window
        main_window = KardexMainWindow(user_info)
        main_window.show()

    # Conectar señal de login exitoso
    login.login_exitoso.connect(on_login_exitoso)
    login.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
