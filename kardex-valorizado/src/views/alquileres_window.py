from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidgetItem, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QMessageBox,
                             QComboBox, QDateEdit, QTextEdit, QTableWidget, QSpinBox, QDoubleSpinBox,
                             QTabWidget, QListWidget, QListWidgetItem, QFileDialog, QRadioButton, QButtonGroup, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap
import sys
import os
from pathlib import Path
from datetime import date, datetime
from views.base_crud_view import BaseCRUDView

from models.database_model import (obtener_session, Alquiler, AlquilerDetalle,
                                   EstadoAlquiler, EstadoEquipo, TipoEquipo,
                                   Equipo, Cliente, AlquilerEvidencia, Proveedor, Producto, TipoItemAlquiler)
from utils.file_manager import FileManager
from utils.widgets import SearchableComboBox, UpperLineEdit
from services.rental_service import RentalService
from services.contract_service import ContractService

class SeleccionKitDialog(QDialog):
    kit_confirmado = pyqtSignal(list) # Emite lista de diccionarios con los detalles

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.detalles_preparados = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Agregar Kit a Alquiler")
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Selección de Kit
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Seleccionar Plantilla (Kit):"))
        self.cmb_kit = SearchableComboBox()
        self.cargar_kits()
        self.cmb_kit.currentIndexChanged.connect(self.cargar_componentes_kit)
        top_layout.addWidget(self.cmb_kit)
        
        # Precio del Kit
        top_layout.addWidget(QLabel("Precio Total Kit (S/):"))
        self.spn_precio_kit = QDoubleSpinBox()
        self.spn_precio_kit.setRange(0, 999999)
        self.spn_precio_kit.setPrefix("S/ ")
        self.spn_precio_kit.valueChanged.connect(self.distribuir_precio_kit)
        top_layout.addWidget(self.spn_precio_kit)
        
        layout.addLayout(top_layout)
        
        # Tabla de Asignación
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(["Componente", "Nivel", "Equipo Asignado", "Estado", "Validación"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_confirm = QPushButton("Confirmar y Agregar")
        btn_confirm.clicked.connect(self.confirmar)
        btn_confirm.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def cargar_kits(self):
        kits = self.session.query(TipoEquipo).filter_by(activo=True).all()
        self.cmb_kit.addItem("Seleccione...", None)
        for k in kits:
            self.cmb_kit.addItem(k.nombre, k.id)

    def cargar_componentes_kit(self):
        self.tabla.setRowCount(0)
        kit_id = self.cmb_kit.currentData()
        if not kit_id: return
        
        kit = self.session.query(TipoEquipo).get(kit_id)
        
        for comp in kit.componentes:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            
            # Nombre Componente
            self.tabla.setItem(row, 0, QTableWidgetItem(comp.nombre_componente))
            
            # Nivel
            nivel_str = comp.nivel_requerido.value if comp.nivel_requerido else "N/A"
            self.tabla.setItem(row, 1, QTableWidgetItem(nivel_str))
            
            # Combo Equipos (Filtrado por Nivel y Disponibilidad)
            cmb_equipos = SearchableComboBox()
            self.llenar_combo_equipos(cmb_equipos, comp.nivel_requerido, comp.equipo_default_id)
            self.tabla.setCellWidget(row, 2, cmb_equipos)
            
            # Estado (Label)
            lbl_estado = QLabel("-")
            lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setCellWidget(row, 3, lbl_estado)
            
            # Validación (Icono/Texto)
            lbl_valid = QLabel("")
            lbl_valid.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setCellWidget(row, 4, lbl_valid)
            
            # Conectar cambio de selección para validar
            # Usamos lambda con captura de argumentos por defecto para evitar problemas de closure
            cmb_equipos.currentIndexChanged.connect(lambda idx, r=row, c=cmb_equipos, l_est=lbl_estado, l_val=lbl_valid: 
                                                    self.validar_seleccion(r, c, l_est, l_val))

    def distribuir_precio_kit(self):
        """Distribuye el precio total del kit proporcionalmente entre los componentes seleccionados"""
        precio_total = self.spn_precio_kit.value()
        if precio_total <= 0: return

        # 1. Calcular suma de tarifas referenciales actuales
        suma_tarifas = 0.0
        componentes_validos = []

        for row in range(self.tabla.rowCount()):
            cmb = self.tabla.cellWidget(row, 2)
            equipo_id = cmb.currentData()
            if equipo_id:
                equipo = self.session.query(Equipo).get(equipo_id)
                if equipo:
                    suma_tarifas += equipo.tarifa_diaria_referencial
                    componentes_validos.append((row, equipo.tarifa_diaria_referencial))

        if suma_tarifas == 0: return

        # 2. Distribuir
        # Guardamos los nuevos precios en una propiedad temporal del widget de la fila o en una lista
        # Para simplificar, asumiremos que al confirmar se recalcula o se usa este valor.
        # Pero el diálogo retorna una lista de dicts.
        # Vamos a almacenar el factor de ajuste.
        self.factor_ajuste = precio_total / suma_tarifas

    def llenar_combo_equipos(self, combo, nivel_requerido, default_id):
        combo.addItem("Seleccionar...", None)
        
        query = self.session.query(Equipo).filter(Equipo.activo == True)
        
        if nivel_requerido:
            query = query.filter(Equipo.nivel == nivel_requerido)
            
        # Solo disponibles o el default (aunque no esté disponible, para mostrarlo)
        # Pero idealmente solo disponibles.
        # query = query.filter(Equipo.estado == EstadoEquipo.DISPONIBLE)
        
        equipos = query.all()
        
        for eq in equipos:
            combo.addItem(f"{eq.codigo} - {eq.nombre}", eq.id)
            
        if default_id:
            idx = combo.findData(default_id)
            if idx >= 0: combo.setCurrentIndex(idx)

    def validar_seleccion(self, row, combo, lbl_estado, lbl_valid):
        equipo_id = combo.currentData()
        if not equipo_id:
            lbl_estado.setText("-")
            lbl_valid.setText("⚠️ Requerido")
            return
            
        equipo = self.session.query(Equipo).get(equipo_id)
        
        # 1. Estado
        lbl_estado.setText(equipo.estado.value)
        if equipo.estado != EstadoEquipo.DISPONIBLE:
            lbl_estado.setStyleSheet("color: red; font-weight: bold;")
            lbl_valid.setText("❌ No Disponible")
            return
        else:
            lbl_estado.setStyleSheet("color: green;")
            
        # 2. Calibración
        if equipo.requiere_calibracion and equipo.fecha_vencimiento_calibracion:
            dias = (equipo.fecha_vencimiento_calibracion - date.today()).days
            if dias < 0:
                lbl_valid.setText("❌ Calib. Vencida")
                lbl_valid.setStyleSheet("color: red; font-weight: bold;")
                return
            elif dias < 30:
                lbl_valid.setText(f"⚠️ Calib. vence {dias}d")
                lbl_valid.setStyleSheet("color: orange; font-weight: bold;")
            else:
                lbl_valid.setText("✅ OK")
                lbl_valid.setStyleSheet("color: green;")
        else:
            lbl_valid.setText("✅ OK")
            lbl_valid.setStyleSheet("color: green;")

    def confirmar(self):
        detalles = []
        errores = False
        
        for row in range(self.tabla.rowCount()):
            cmb = self.tabla.cellWidget(row, 2)
            equipo_id = cmb.currentData()
            
            # Verificar si es opcional (necesitaría pasar ese dato, por ahora asumimos obligatorio si está en la lista)
            # Simplificación: Si no selecciona nada, error.
            if not equipo_id:
                errores = True
                break
                
            # Verificar validación visual
            lbl_valid = self.tabla.cellWidget(row, 4)
            if "❌" in lbl_valid.text():
                errores = True
                break
                
            equipo = self.session.query(Equipo).get(equipo_id)
            
            # Aplicar precio ajustado si hay un precio de kit definido
            tarifa_final = equipo.tarifa_diaria_referencial
            if hasattr(self, 'factor_ajuste') and self.spn_precio_kit.value() > 0:
                tarifa_final = equipo.tarifa_diaria_referencial * self.factor_ajuste
            
            detalles.append({
                'equipo_id': equipo_id,
                'cantidad': 1,
                'tarifa': tarifa_final
            })
            
        if errores:
            QMessageBox.warning(self, "Error", "Hay componentes sin asignar o con validaciones fallidas.")
            return
            
        self.kit_confirmado.emit(detalles)
        self.accept()

class EvidenciaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ruta_archivo = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Agregar Evidencia")
        self.setFixedSize(400, 300)
        layout = QVBoxLayout()
        
        # Tipo
        grp_tipo = QGroupBox("Tipo")
        hbox = QHBoxLayout()
        self.rb_salida = QRadioButton("Salida")
        self.rb_salida.setChecked(True)
        self.rb_retorno = QRadioButton("Retorno")
        hbox.addWidget(self.rb_salida)
        hbox.addWidget(self.rb_retorno)
        grp_tipo.setLayout(hbox)
        layout.addWidget(grp_tipo)
        
        # Foto
        self.lbl_preview = QLabel("Sin archivo seleccionado")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("border: 1px dashed #ccc; height: 100px;")
        layout.addWidget(self.lbl_preview)
        
        btn_foto = QPushButton("Seleccionar Foto/Video...")
        btn_foto.clicked.connect(self.seleccionar_foto)
        layout.addWidget(btn_foto)
        
        # Comentario
        layout.addWidget(QLabel("Comentario:"))
        self.txt_comentario = QTextEdit()
        self.txt_comentario.setMaximumHeight(60)
        layout.addWidget(self.txt_comentario)
        
        # Botones
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Guardar")
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)
        
        self.setLayout(layout)
        
    def seleccionar_foto(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo", "", "Multimedia (*.png *.jpg *.jpeg *.mp4 *.avi *.mov)")
        if file_name:
            self.ruta_archivo = file_name
            self.lbl_preview.setText(Path(file_name).name)
            if FileManager.is_video(file_name):
                self.lbl_preview.setStyleSheet("border: 1px solid blue; color: blue; font-weight: bold;")
            else:
                self.lbl_preview.setStyleSheet("border: 1px solid green; color: green;")

    def get_data(self):
        tipo = "SALIDA" if self.rb_salida.isChecked() else "RETORNO"
        return self.ruta_archivo, tipo, self.txt_comentario.toPlainText()

class AddItemDialog(QDialog):
    item_confirmado = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Agregar Equipo al Alquiler")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        # Equipo
        self.cmb_equipo = SearchableComboBox()
        self.cargar_equipos()
        self.cmb_equipo.currentIndexChanged.connect(self.actualizar_tarifa)
        form.addRow("Equipo:*", self.cmb_equipo)
        
        # Tarifa
        self.spn_tarifa = QDoubleSpinBox()
        self.spn_tarifa.setRange(0, 999999)
        self.spn_tarifa.setPrefix("S/ ")
        form.addRow("Tarifa Diaria:", self.spn_tarifa)
        
        # Sub-alquiler Checkbox
        self.chk_subalquiler = QCheckBox("Es Sub-alquiler (Re-renta)")
        self.chk_subalquiler.toggled.connect(self.toggle_subalquiler)
        form.addRow("", self.chk_subalquiler)
        
        # Sub-alquiler Fields (Hidden by default)
        self.grp_sub = QGroupBox("Detalles Sub-alquiler")
        self.grp_sub.setVisible(False)
        sub_layout = QFormLayout()
        
        self.cmb_proveedor = SearchableComboBox()
        self.cargar_proveedores()
        sub_layout.addRow("Proveedor:*", self.cmb_proveedor)
        
        self.spn_costo = QDoubleSpinBox()
        self.spn_costo.setRange(0, 999999)
        self.spn_costo.setPrefix("S/ ")
        sub_layout.addRow("Costo Diario:*", self.spn_costo)
        
        self.grp_sub.setLayout(sub_layout)
        layout.addLayout(form)
        layout.addWidget(self.grp_sub)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_add = QPushButton("Agregar")
        btn_add.clicked.connect(self.confirmar)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_add)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def cargar_equipos(self):
        equipos = self.session.query(Equipo).filter(Equipo.activo == True).all()
        self.cmb_equipo.addItem("Seleccione...", None)
        for eq in equipos:
            # Show status if not available
            status = "" if eq.estado == EstadoEquipo.DISPONIBLE else f" ({eq.estado.value})"
            self.cmb_equipo.addItem(f"{eq.codigo} - {eq.nombre}{status}", eq.id)

    def cargar_proveedores(self):
        proveedores = self.session.query(Proveedor).filter(Proveedor.activo == True).all()
        self.cmb_proveedor.addItem("Seleccione...", None)
        for p in proveedores:
            self.cmb_proveedor.addItem(p.razon_social, p.id)

    def actualizar_tarifa(self):
        equipo_id = self.cmb_equipo.currentData()
        if equipo_id:
            equipo = self.session.query(Equipo).get(equipo_id)
            if equipo:
                self.spn_tarifa.setValue(equipo.tarifa_diaria_referencial)

    def toggle_subalquiler(self, checked):
        self.grp_sub.setVisible(checked)

    def confirmar(self):
        equipo_id = self.cmb_equipo.currentData()
        if not equipo_id:
            QMessageBox.warning(self, "Error", "Seleccione un equipo.")
            return
            
        tarifa = self.spn_tarifa.value()
        
        es_sub = self.chk_subalquiler.isChecked()
        prov_id = None
        costo = 0.0
        
        if es_sub:
            prov_id = self.cmb_proveedor.currentData()
            if not prov_id:
                QMessageBox.warning(self, "Error", "Seleccione un proveedor para el sub-alquiler.")
                return
            costo = self.spn_costo.value()
            
        data = {
            'equipo_id': equipo_id,
            'cantidad': 1,
            'tarifa': tarifa,
            'es_subalquiler': es_sub,
            'proveedor_id': prov_id,
            'costo_subalquiler': costo
        }
        
        self.item_confirmado.emit(data)
        self.accept()

class AddConsumableDialog(QDialog):
    consumible_confirmado = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Agregar Consumible")
        self.setFixedSize(400, 250)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.cmb_producto = SearchableComboBox()
        self.cargar_productos()
        self.cmb_producto.currentIndexChanged.connect(self.actualizar_precio)
        form.addRow("Producto:*", self.cmb_producto)
        
        self.spn_cantidad = QDoubleSpinBox()
        self.spn_cantidad.setRange(0.01, 999999)
        self.spn_cantidad.setValue(1.0)
        form.addRow("Cantidad:", self.spn_cantidad)
        
        self.spn_precio = QDoubleSpinBox()
        self.spn_precio.setRange(0, 999999)
        self.spn_precio.setPrefix("S/ ")
        form.addRow("Precio Unit.:", self.spn_precio)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_add = QPushButton("Agregar")
        btn_add.clicked.connect(self.confirmar)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_add)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def cargar_productos(self):
        # Cargar todos los productos (idealmente filtrar por categoría 'Consumibles' si existiera flag)
        productos = self.session.query(Producto).filter(Producto.activo == True).all()
        self.cmb_producto.addItem("Seleccione...", None)
        for p in productos:
            self.cmb_producto.addItem(f"{p.codigo} - {p.nombre}", p.id)

    def actualizar_precio(self):
        prod_id = self.cmb_producto.currentData()
        if prod_id:
            prod = self.session.query(Producto).get(prod_id)
            if prod and prod.precio_venta:
                self.spn_precio.setValue(prod.precio_venta)

    def confirmar(self):
        prod_id = self.cmb_producto.currentData()
        if not prod_id:
            QMessageBox.warning(self, "Error", "Seleccione un producto.")
            return
            
        data = {
            'producto_id': prod_id,
            'cantidad': self.spn_cantidad.value(),
            'tarifa': self.spn_precio.value(),
            'tipo_item': 'CONSUMIBLE'
        }
        self.consumible_confirmado.emit(data)
        self.accept()

class AlquilerDialog(QDialog):
    """Diálogo para crear/editar Alquiler"""
    alquiler_guardado = pyqtSignal()

    def __init__(self, parent=None, alquiler=None, cotizacion_data=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.alquiler = alquiler
        self.cotizacion_data = cotizacion_data
        self.detalles_temp = [] # Lista de dicts
        self.init_ui()
        
        if alquiler:
            self.cargar_datos()
        elif cotizacion_data:
            self.cargar_datos_cotizacion()

    def init_ui(self):
        self.setWindowTitle("Nuevo Alquiler" if not self.alquiler else "Editar Alquiler")
        self.setFixedSize(900, 700)
        
        layout = QVBoxLayout()
        
        # --- TABS ---
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # TAB 1: General y Detalles
        tab_general = QWidget()
        layout_general = QVBoxLayout()
        
        # --- CABECERA ---
        grp_header = QGroupBox("Datos Generales")
        form = QFormLayout()
        
        self.cmb_cliente = SearchableComboBox()
        self.cargar_clientes()
        form.addRow("Cliente:*", self.cmb_cliente)
        
        self.txt_obra = UpperLineEdit()
        form.addRow("Ubicación Obra:", self.txt_obra)
        
        fechas_layout = QHBoxLayout()
        self.date_inicio = QDateEdit(date.today())
        self.date_inicio.setCalendarPopup(True)
        self.date_fin = QDateEdit(date.today().replace(day=date.today().day + 1)) # +1 día default (simple logic)
        self.date_fin.setCalendarPopup(True)
        
        fechas_layout.addWidget(QLabel("Inicio:"))
        fechas_layout.addWidget(self.date_inicio)
        fechas_layout.addWidget(QLabel("Fin Est.:"))
        fechas_layout.addWidget(self.date_fin)
        form.addRow("Fechas:", fechas_layout)
        
        grp_header.setLayout(form)
        layout_general.addWidget(grp_header)
        
        # --- DETALLES ---
        grp_detalles = QGroupBox("Equipos y Productos")
        det_layout = QVBoxLayout()
        
        toolbar_det = QHBoxLayout()
        btn_add_kit = QPushButton("📦 Agregar Kit")
        btn_add_kit.clicked.connect(self.agregar_kit)
        btn_add_item = QPushButton("➕ Agregar Equipo Suelto")
        btn_add_item.clicked.connect(self.agregar_item_suelto)
        
        btn_add_item = QPushButton("➕ Agregar Equipo Suelto")
        btn_add_item.clicked.connect(self.agregar_item_suelto)
        
        btn_add_cons = QPushButton("🛒 Agregar Consumible")
        btn_add_cons.clicked.connect(self.agregar_consumible)
        
        toolbar_det.addWidget(btn_add_kit)
        toolbar_det.addWidget(btn_add_item)
        toolbar_det.addWidget(btn_add_cons)
        toolbar_det.addStretch()
        
        det_layout.addLayout(toolbar_det)
        
        self.tabla_detalles = QTableWidget()
        self.tabla_detalles.setColumnCount(8)
        self.tabla_detalles.setHorizontalHeaderLabels(["Código", "Descripción", "Cant.", "Tarifa", "H. Salida", "H. Retorno", "H. Uso", "Subtotal"])
        self.tabla_detalles.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        det_layout.addWidget(self.tabla_detalles)
        
        grp_detalles.setLayout(det_layout)
        layout_general.addWidget(grp_detalles)
        
        tab_general.setLayout(layout_general)
        self.tabs.addTab(tab_general, "General")
        
        # TAB 2: Evidencias
        self.tab_evidencias = QWidget()
        self.init_tab_evidencias()
        self.tabs.addTab(self.tab_evidencias, "Evidencias / Fotos")
        
        # --- FOOTER ---
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Guardar Alquiler")
        btn_save.clicked.connect(self.guardar)
        btn_save.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 10px;")
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def init_tab_evidencias(self):
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QHBoxLayout()
        btn_add_evidencia = QPushButton("📷/🎥 Agregar Evidencia")
        btn_add_evidencia.clicked.connect(self.agregar_evidencia)
        toolbar.addWidget(btn_add_evidencia)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Lista de fotos
        self.lista_evidencias = QListWidget()
        self.lista_evidencias.setViewMode(QListWidget.ViewMode.IconMode)
        self.lista_evidencias.setIconSize(QSize(150, 150))
        self.lista_evidencias.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.lista_evidencias.setSpacing(10)
        layout.addWidget(self.lista_evidencias)
        
        self.tab_evidencias.setLayout(layout)

    def agregar_evidencia(self):
        if not self.alquiler:
            QMessageBox.warning(self, "Aviso", "Primero debe guardar el alquiler para agregar evidencias.")
            return

        dialog = EvidenciaDialog(self)
        if dialog.exec():
            ruta, tipo, comentario = dialog.get_data()
            
            # Determinar carpeta según tipo
            carpeta = "salida_equipos" if tipo == "SALIDA" else "devolucion_equipos"
            
            # Guardar archivo
            nueva_ruta = FileManager.save_file(ruta, carpeta, prefix=f"evidencia_{self.alquiler.id}")
            
            # Guardar en BD
            evidencia = AlquilerEvidencia(
                alquiler_id=self.alquiler.id,
                ruta_archivo=nueva_ruta,
                tipo=tipo,
                comentario=comentario
            )
            self.session.add(evidencia)
            self.session.commit()
            
            self.cargar_evidencias()

    def cargar_evidencias(self):
        self.lista_evidencias.clear()
        if not self.alquiler: return
        
        evidencias = self.session.query(AlquilerEvidencia).filter_by(alquiler_id=self.alquiler.id).all()
        
        for ev in evidencias:
            full_path = FileManager.get_full_path(ev.ruta_archivo)
            if full_path and os.path.exists(full_path):
                if FileManager.is_video(full_path):
                    # Icono de video genérico o texto
                    icon = self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay)
                    texto = f"[VIDEO] {ev.tipo}\n{ev.comentario}"
                else:
                    icon = QIcon(full_path)
                    texto = f"{ev.tipo}\n{ev.comentario}"
                    
                item = QListWidgetItem(icon, texto)
                item.setSizeHint(QSize(160, 200))
                self.lista_evidencias.addItem(item)

    def cargar_clientes(self):
        clientes = self.session.query(Cliente).filter_by(activo=True).all()
        for c in clientes:
            self.cmb_cliente.addItem(c.razon_social_o_nombre, c.id)

    def agregar_kit(self):
        dialog = SeleccionKitDialog(self)
        dialog.kit_confirmado.connect(self.recibir_detalles_kit)
        dialog.exec()

    def recibir_detalles_kit(self, detalles):
        for det in detalles:
            self.detalles_temp.append(det)
        self.actualizar_tabla_detalles()

    def agregar_item_suelto(self):
        dialog = AddItemDialog(self)
        dialog.item_confirmado.connect(self.recibir_item_suelto)
        dialog.exec()

    def recibir_item_suelto(self, data):
        self.detalles_temp.append(data)
        self.actualizar_tabla_detalles()

    def agregar_consumible(self):
        dialog = AddConsumableDialog(self)
        dialog.consumible_confirmado.connect(self.recibir_consumible)
        dialog.exec()

    def recibir_consumible(self, data):
        self.detalles_temp.append(data)
        self.actualizar_tabla_detalles()

    def actualizar_tabla_detalles(self):
        self.tabla_detalles.setRowCount(0)
        total = 0.0
        for row_idx, det in enumerate(self.detalles_temp):
            self.tabla_detalles.insertRow(row_idx)
            
            # 0: Código
            # 1: Descripción
            
            tipo = det.get('tipo_item', 'EQUIPO')
            
            if tipo == 'CONSUMIBLE':
                prod = self.session.query(Producto).get(det['producto_id'])
                self.tabla_detalles.setItem(row_idx, 0, QTableWidgetItem(prod.codigo))
                self.tabla_detalles.setItem(row_idx, 1, QTableWidgetItem(f"[CONSUMIBLE] {prod.nombre}"))
                
                # Deshabilitar horómetros para consumibles
                item_salida = QTableWidgetItem("-")
                item_salida.setFlags(Qt.ItemFlag.NoItemFlags)
                self.tabla_detalles.setItem(row_idx, 4, item_salida)
                
                item_retorno = QTableWidgetItem("-")
                item_retorno.setFlags(Qt.ItemFlag.NoItemFlags)
                self.tabla_detalles.setItem(row_idx, 5, item_retorno)
                
                self.tabla_detalles.setItem(row_idx, 6, QTableWidgetItem("-"))
                
            else:
                equipo = self.session.query(Equipo).get(det['equipo_id'])
                self.tabla_detalles.setItem(row_idx, 0, QTableWidgetItem(equipo.codigo))
                nombre_equipo = equipo.nombre
                if det.get('es_subalquiler'):
                    nombre_equipo += " (SUB-ALQUILER)"
                self.tabla_detalles.setItem(row_idx, 1, QTableWidgetItem(nombre_equipo))
                
                # 4: H. Salida (Editable)
                h_salida = det.get('horometro_salida', equipo.horometro_actual)
                item_salida = QTableWidgetItem(str(h_salida))
                self.tabla_detalles.setItem(row_idx, 4, item_salida)
                
                # 5: H. Retorno (Editable)
                h_retorno = det.get('horometro_retorno', 0.0)
                item_retorno = QTableWidgetItem(str(h_retorno))
                self.tabla_detalles.setItem(row_idx, 5, item_retorno)
                
                # 6: H. Uso (Calculated)
                h_uso = 0.0
                if h_retorno > h_salida:
                    h_uso = h_retorno - h_salida
                self.tabla_detalles.setItem(row_idx, 6, QTableWidgetItem(f"{h_uso:.1f}"))
            
            # 7: Subtotal
            subtotal = det['cantidad'] * det['tarifa']
            self.tabla_detalles.setItem(row_idx, 7, QTableWidgetItem(f"{subtotal:.2f}"))
            total += subtotal
            
        # Connect itemChanged to update temp list
        try:
            self.tabla_detalles.itemChanged.disconnect(self.on_detail_changed)
        except:
            pass
        self.tabla_detalles.itemChanged.connect(self.on_detail_changed)

    def on_detail_changed(self, item):
        row = item.row()
        col = item.column()
        
        if row < 0 or row >= len(self.detalles_temp): return
        
        try:
            val = float(item.text())
        except ValueError:
            return

        det = self.detalles_temp[row]
        
        if col == 4: # H. Salida
            det['horometro_salida'] = val
        elif col == 5: # H. Retorno
            det['horometro_retorno'] = val
            
        # Recalculate usage if needed (optional, or re-render row)


    def cargar_datos(self):
        if not self.alquiler: return
        
        self.date_inicio.setDate(self.alquiler.fecha_inicio)
        if self.alquiler.fecha_fin_estimada:
            self.date_fin.setDate(self.alquiler.fecha_fin_estimada)
            
        index = self.cmb_cliente.findData(self.alquiler.cliente_id)
        if index >= 0: self.cmb_cliente.setCurrentIndex(index)
        
        self.txt_obra.setText(self.alquiler.ubicacion_obra or "")
        
        # Cargar detalles
        self.detalles_temp = []
        for det in self.alquiler.detalles:
            if det.tipo_item == TipoItemAlquiler.CONSUMIBLE:
                 self.detalles_temp.append({
                    'producto_id': det.producto_id,
                    'cantidad': det.cantidad or 1,
                    'tarifa': det.precio_unitario,
                    'tipo_item': 'CONSUMIBLE'
                })
            else:
                self.detalles_temp.append({
                    'equipo_id': det.equipo_id,
                    'cantidad': 1, 
                    'tarifa': det.precio_unitario,
                    'horometro_salida': det.horometro_salida,
                    'horometro_retorno': det.horometro_retorno,
                    'tipo_item': 'EQUIPO'
                })
        self.actualizar_tabla_detalles()
        
        self.cargar_evidencias()


    def cargar_datos_cotizacion(self):
        if not self.cotizacion_data: return
        
        # Cliente
        cliente_id = self.cotizacion_data.get('cliente_id')
        if cliente_id:
            index = self.cmb_cliente.findData(cliente_id)
            if index >= 0: self.cmb_cliente.setCurrentIndex(index)
            
        # Observaciones
        obs = self.cotizacion_data.get('observaciones', '')
        num = self.cotizacion_data.get('numero_cotizacion', '')
        self.setWindowTitle(f"Nuevo Alquiler (Desde {num})")
        
        # Intentar cargar items (Simplificado: Solo mensaje por ahora si no hay mapeo directo)
        # En una versión avanzada, aquí iteraríamos los detalles de la cotización
        # e intentaríamos buscar equipos disponibles que coincidan con el producto.

    def guardar(self):
        cliente_id = self.cmb_cliente.currentData()
        if not cliente_id:
            QMessageBox.warning(self, "Error", "Seleccione un cliente.")
            return
            
        try:
            if not self.alquiler:
                self.alquiler = Alquiler(
                    cliente_id=cliente_id,
                    fecha_inicio=self.date_inicio.date().toPyDate(),
                    fecha_fin_estimada=self.date_fin.date().toPyDate(),
                    ubicacion_obra=self.txt_obra.text(),
                    estado=EstadoAlquiler.ACTIVO # Directamente activo para probar
                )
                self.session.add(self.alquiler)
                self.session.flush() # Para tener ID
                
                # Guardar detalles
                # Guardar detalles
                # Guardar detalles
                for det in self.detalles_temp:
                    tipo = det.get('tipo_item', 'EQUIPO')
                    
                    if tipo == 'CONSUMIBLE':
                        nuevo_det = AlquilerDetalle(
                            alquiler_id=self.alquiler.id,
                            producto_id=det['producto_id'],
                            tipo_item=TipoItemAlquiler.CONSUMIBLE,
                            cantidad=det['cantidad'],
                            precio_unitario=det['tarifa'],
                            total=det['cantidad'] * det['tarifa'],
                            fecha_salida=self.date_inicio.date().toPyDate()
                        )
                        self.session.add(nuevo_det)
                    else:
                        equipo = self.session.query(Equipo).get(det['equipo_id'])
                        
                        h_salida = det.get('horometro_salida', equipo.horometro_actual)
                        h_retorno = det.get('horometro_retorno', 0.0)
                        h_uso = 0.0
                        if h_retorno > h_salida:
                            h_uso = h_retorno - h_salida
                            
                        # Update Equipo Horometer if returned
                        if h_retorno > 0:
                            if h_retorno > equipo.horometro_actual:
                                equipo.horometro_actual = h_retorno
                                
                        nuevo_det = AlquilerDetalle(
                            alquiler_id=self.alquiler.id,
                            equipo_id=det['equipo_id'],
                            tipo_item=TipoItemAlquiler.EQUIPO,
                            
                            precio_unitario=det['tarifa'],
                            total=det['cantidad'] * det['tarifa'],
                            
                            horometro_salida=h_salida,
                            horometro_retorno=h_retorno,
                            horas_uso=h_uso,
                            
                            fecha_salida=self.date_inicio.date().toPyDate(),
                            
                            # Sub-alquiler
                            es_subalquiler=det.get('es_subalquiler', False),
                            proveedor_subalquiler_id=det.get('proveedor_id'),
                            costo_subalquiler=det.get('costo_subalquiler', 0.0)
                        )
                        self.session.add(nuevo_det)
                        
                        # Actualizar estado del equipo
                        equipo.estado = EstadoEquipo.ALQUILADO
            
            self.session.commit()
            self.alquiler_guardado.emit()
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class BillingPreviewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = RentalService()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Proyección de Facturación")
        self.resize(1000, 600)
        
        layout = QVBoxLayout()
        
        # Filters
        filter_layout = QHBoxLayout()
        
        self.date_start = QDateEdit(date.today().replace(day=1))
        self.date_start.setCalendarPopup(True)
        
        self.date_end = QDateEdit(date.today())
        self.date_end.setCalendarPopup(True)
        
        btn_calc = QPushButton("Calcular")
        btn_calc.clicked.connect(self.calculate)
        
        filter_layout.addWidget(QLabel("Desde:"))
        filter_layout.addWidget(self.date_start)
        filter_layout.addWidget(QLabel("Hasta:"))
        filter_layout.addWidget(self.date_end)
        filter_layout.addWidget(btn_calc)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Cliente", "Equipo", "Código", "Inicio Periodo", "Fin Periodo", "Días", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.lbl_total = QLabel("Total General: S/ 0.00")
        self.lbl_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ecc71;")
        layout.addWidget(self.lbl_total)
        
        self.setLayout(layout)
        
    def calculate(self):
        start = self.date_start.date().toPyDate()
        end = self.date_end.date().toPyDate()
        
        data = self.service.get_pending_billing(start, end)
        
        self.table.setRowCount(0)
        total_general = 0.0
        
        for row, item in enumerate(data):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item['cliente']))
            self.table.setItem(row, 1, QTableWidgetItem(item['equipo']))
            self.table.setItem(row, 2, QTableWidgetItem(item['codigo_equipo']))
            self.table.setItem(row, 3, QTableWidgetItem(item['periodo_inicio'].strftime("%d/%m/%Y")))
            self.table.setItem(row, 4, QTableWidgetItem(item['periodo_fin'].strftime("%d/%m/%Y")))
            self.table.setItem(row, 5, QTableWidgetItem(str(item['dias'])))
            self.table.setItem(row, 6, QTableWidgetItem(f"S/ {item['total']:.2f}"))
            
            total_general += item['total']
            
        self.lbl_total.setText(f"Total General: S/ {total_general:.2f}")

    def closeEvent(self, event):
        self.service.close()
        super().closeEvent(event)

class PartialReturnDialog(QDialog):
    return_confirmed = pyqtSignal()

    def __init__(self, parent=None, alquiler=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.alquiler = alquiler
        self.init_ui()
        self.cargar_items_pendientes()

    def init_ui(self):
        self.setWindowTitle(f"Devolución de Equipos - Contrato {self.alquiler.numero_contrato}")
        self.resize(800, 500)
        
        layout = QVBoxLayout()
        
        # Header
        form = QFormLayout()
        self.date_retorno = QDateEdit(date.today())
        self.date_retorno.setCalendarPopup(True)
        form.addRow("Fecha de Devolución:", self.date_retorno)
        layout.addLayout(form)
        
        layout.addWidget(QLabel("Seleccione los ítems a devolver:"))
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Devolver", "Equipo/Item", "Código", "H. Salida", "H. Retorno", "Notas"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Registrar Devolución")
        btn_save.clicked.connect(self.guardar)
        btn_save.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold;")
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def cargar_items_pendientes(self):
        self.table.setRowCount(0)
        # Filtrar detalles no devueltos
        detalles_pendientes = [d for d in self.alquiler.detalles if not d.fecha_retorno]
        
        for row, det in enumerate(detalles_pendientes):
            self.table.insertRow(row)
            
            # Checkbox
            chk = QCheckBox()
            cell_widget = QWidget()
            layout_chk = QHBoxLayout(cell_widget)
            layout_chk.addWidget(chk)
            layout_chk.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_chk.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(row, 0, cell_widget)
            
            # Store detail ID in checkbox or widget property
            chk.setProperty("detalle_id", det.id)
            
            # Info
            nombre = det.equipo.nombre if det.equipo else (det.producto.nombre if det.producto else "Item")
            codigo = det.equipo.codigo if det.equipo else (det.producto.codigo if det.producto else "-")
            
            self.table.setItem(row, 1, QTableWidgetItem(nombre))
            self.table.setItem(row, 2, QTableWidgetItem(codigo))
            
            # Horometros
            h_salida = det.horometro_salida or 0.0
            self.table.setItem(row, 3, QTableWidgetItem(str(h_salida)))
            
            # H. Retorno (Editable)
            if det.tipo_item == TipoItemAlquiler.CONSUMIBLE:
                 self.table.setItem(row, 4, QTableWidgetItem("-"))
                 chk.setEnabled(False) # Consumables usually don't return? Or maybe unused ones?
                 # Assuming consumables are sold/used, not returned.
                 # If partial return of consumables is allowed (e.g. return unused fuel), logic is complex.
                 # For now disable return of consumables.
                 chk.setToolTip("Los consumibles no se devuelven (se facturan).")
            else:
                item_retorno = QTableWidgetItem(str(h_salida)) # Default to same
                self.table.setItem(row, 4, item_retorno)
            
            self.table.setItem(row, 5, QTableWidgetItem("")) # Notas

    def guardar(self):
        fecha_retorno = self.date_retorno.date().toPyDate()
        items_devueltos = 0
        
        try:
            for row in range(self.table.rowCount()):
                cell_widget = self.table.cellWidget(row, 0)
                chk = cell_widget.findChild(QCheckBox)
                
                if chk.isChecked():
                    det_id = chk.property("detalle_id")
                    detalle = self.session.get(AlquilerDetalle, det_id)
                    
                    if detalle:
                        # Validar fecha
                        if fecha_retorno < detalle.fecha_salida.date():
                            QMessageBox.warning(self, "Error", f"La fecha de retorno no puede ser anterior a la salida ({detalle.fecha_salida.date()}) para el item {detalle.equipo.codigo}.")
                            return

                        # Horometro
                        h_retorno_val = 0.0
                        item_h = self.table.item(row, 4)
                        if item_h and item_h.text() != "-":
                            try:
                                h_retorno_val = float(item_h.text())
                            except ValueError:
                                QMessageBox.warning(self, "Error", f"Horómetro inválido en fila {row+1}")
                                return
                                
                            if h_retorno_val < detalle.horometro_salida:
                                QMessageBox.warning(self, "Error", f"El horómetro de retorno no puede ser menor al de salida ({detalle.horometro_salida}) en fila {row+1}")
                                return
                        
                        # Actualizar Detalle
                        detalle.fecha_retorno = datetime.combine(fecha_retorno, datetime.min.time())
                        detalle.horometro_retorno = h_retorno_val
                        detalle.horas_uso = h_retorno_val - detalle.horometro_salida
                        
                        # Actualizar Equipo
                        if detalle.equipo:
                            detalle.equipo.estado = EstadoEquipo.DISPONIBLE
                            detalle.equipo.horometro_actual = h_retorno_val
                            # Check maintenance logic here? (Phase 4)
                        
                        items_devueltos += 1
            
            if items_devueltos > 0:
                # Verificar si todos los items fueron devueltos para cerrar alquiler
                # Recargar alquiler para ver estado actual de detalles
                self.session.flush()
                pendientes = [d for d in self.alquiler.detalles if not d.fecha_retorno and d.tipo_item != TipoItemAlquiler.CONSUMIBLE]
                
                if not pendientes:
                    reply = QMessageBox.question(self, "Cerrar Alquiler", "Todos los equipos han sido devueltos. ¿Desea finalizar el contrato?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        self.alquiler.estado = EstadoAlquiler.FINALIZADO
                        self.alquiler.fecha_fin_real = fecha_retorno
                
                self.session.commit()
                self.return_confirmed.emit()
                self.accept()
            else:
                QMessageBox.warning(self, "Aviso", "No seleccionó ningún ítem para devolver.")
                
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class ExtensionDialog(QDialog):
    extension_confirmed = pyqtSignal()

    def __init__(self, parent=None, alquiler=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.alquiler = alquiler
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Extender Alquiler - {self.alquiler.numero_contrato}")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.lbl_actual = QLabel(self.alquiler.fecha_fin_estimada.strftime("%d/%m/%Y"))
        form.addRow("Fecha Fin Actual:", self.lbl_actual)
        
        self.date_nueva = QDateEdit(self.alquiler.fecha_fin_estimada)
        self.date_nueva.setCalendarPopup(True)
        self.date_nueva.setMinimumDate(QDate(self.alquiler.fecha_fin_estimada.year, self.alquiler.fecha_fin_estimada.month, self.alquiler.fecha_fin_estimada.day))
        form.addRow("Nueva Fecha Fin:", self.date_nueva)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar Extensión")
        btn_save.clicked.connect(self.guardar)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def guardar(self):
        nueva_fecha = self.date_nueva.date().toPyDate()
        if nueva_fecha <= self.alquiler.fecha_fin_estimada:
            QMessageBox.warning(self, "Error", "La nueva fecha debe ser posterior a la actual.")
            return
            
        try:
            self.alquiler.fecha_fin_estimada = nueva_fecha
            self.session.commit()
            QMessageBox.information(self, "Éxito", "Alquiler extendido correctamente.")
            self.extension_confirmed.emit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class AlquileresWindow(BaseCRUDView):
    """Ventana de gestión de Alquileres"""
    
    def __init__(self):
        super().__init__("Gestión de Alquileres", Alquiler, AlquilerDialog)
        
        # Add Billing Button to toolbar (accessing parent layout or adding to top)
        # BaseCRUDView structure might need inspection, but usually we can add to self.layout()
        
        btn_billing = QPushButton("💰 Proyección Facturación")
        btn_billing.clicked.connect(self.open_billing_preview)
        
        btn_contract = QPushButton("📄 Generar Contrato")
        btn_contract.clicked.connect(self.generar_contrato)
        
        btn_return = QPushButton("🔙 Devolución / Retorno")
        btn_return.clicked.connect(self.open_return_dialog)
        
        btn_extend = QPushButton("📅 Extender Plazo")
        btn_extend.clicked.connect(self.open_extension_dialog)
        
        btn_acta_entrega = QPushButton("📄 Acta Entrega")
        btn_acta_entrega.clicked.connect(self.generar_acta_entrega)
        
        btn_acta_devolucion = QPushButton("📄 Acta Devolución")
        btn_acta_devolucion.clicked.connect(self.generar_acta_devolucion)
        
        # Insert at top
        self.layout().insertWidget(0, btn_billing)
        self.layout().insertWidget(1, btn_contract)
        self.layout().insertWidget(2, btn_return)
        self.layout().insertWidget(3, btn_extend)
        self.layout().insertWidget(4, btn_acta_entrega)
        self.layout().insertWidget(5, btn_acta_devolucion)

    def open_billing_preview(self):
        dialog = BillingPreviewDialog(self)
        dialog.exec()

    def generar_contrato(self):
        selected_row = self.tabla.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Aviso", "Seleccione un alquiler para generar el contrato.")
            return
            
        alquiler_id = int(self.tabla.item(selected_row, 0).text())
        alquiler = self.session.get(Alquiler, alquiler_id)
        
        if not alquiler:
            return
            
        file_name, _ = QFileDialog.getSaveFileName(self, "Guardar Contrato PDF", f"Contrato_{alquiler.id}.pdf", "PDF Files (*.pdf)")
        if file_name:
            try:
                service = ContractService()
                service.generate_contract(alquiler, file_name)
                QMessageBox.information(self, "Éxito", f"Contrato generado correctamente en:\n{file_name}")
                
                # Open file
                os.startfile(file_name)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al generar contrato:\n{str(e)}")

    def open_return_dialog(self):
        selected_row = self.tabla.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Aviso", "Seleccione un alquiler para registrar devolución.")
            return
            
        alquiler_id = int(self.tabla.item(selected_row, 0).text())
        alquiler = self.session.get(Alquiler, alquiler_id)
        
        if not alquiler: return
        
        dialog = PartialReturnDialog(self, alquiler)
        dialog.return_confirmed.connect(self.load_data)
        dialog.exec()

    def open_extension_dialog(self):
        selected_row = self.tabla.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Aviso", "Seleccione un alquiler para extender.")
            return
            
        alquiler_id = int(self.tabla.item(selected_row, 0).text())
        alquiler = self.session.get(Alquiler, alquiler_id)
        
        if not alquiler: return
        
        dialog = ExtensionDialog(self, alquiler)
        dialog.extension_confirmed.connect(self.load_data)
        dialog.exec()

    def generar_acta_entrega(self):
        self._generar_documento("entrega")

    def generar_acta_devolucion(self):
        self._generar_documento("devolucion")

    def _generar_documento(self, tipo):
        selected_row = self.tabla.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Aviso", "Seleccione un alquiler.")
            return
            
        alquiler_id = int(self.tabla.item(selected_row, 0).text())
        alquiler = self.session.get(Alquiler, alquiler_id)
        
        if not alquiler: return
        
        nombre_doc = f"Acta_{tipo.capitalize()}_{alquiler.id}.pdf"
        file_name, _ = QFileDialog.getSaveFileName(self, f"Guardar Acta {tipo.capitalize()}", nombre_doc, "PDF Files (*.pdf)")
        
        if file_name:
            try:
                service = ContractService()
                if tipo == "entrega":
                    service.generate_delivery_act(alquiler, file_name)
                else:
                    service.generate_return_act(alquiler, file_name)
                    
                QMessageBox.information(self, "Éxito", f"Documento generado correctamente en:\n{file_name}")
                os.startfile(file_name)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al generar documento:\n{str(e)}")



        
    def setup_table_columns(self):
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Cliente", "Obra", "Inicio", "Fin Est.", "Estado", "Acciones"
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setColumnWidth(6, 180)
        
    def fill_row(self, row, item):
        self.tabla.setItem(row, 0, QTableWidgetItem(str(item.id)))
        self.tabla.setItem(row, 1, QTableWidgetItem(item.cliente.razon_social_o_nombre))
        self.tabla.setItem(row, 2, QTableWidgetItem(item.ubicacion_obra or ""))
        self.tabla.setItem(row, 3, QTableWidgetItem(item.fecha_inicio.strftime("%d/%m/%Y")))
        self.tabla.setItem(row, 4, QTableWidgetItem(item.fecha_fin_estimada.strftime("%d/%m/%Y") if item.fecha_fin_estimada else "-"))
        self.tabla.setItem(row, 5, QTableWidgetItem(item.estado.value))

    def _open_dialog(self, item=None):
        dialog = AlquilerDialog(self, alquiler=item)
        dialog.alquiler_guardado.connect(self.load_data)
        dialog.exec()
