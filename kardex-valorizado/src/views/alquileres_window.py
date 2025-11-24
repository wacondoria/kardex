from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidgetItem, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QMessageBox,
                             QComboBox, QDateEdit, QTextEdit, QTableWidget, QSpinBox, QDoubleSpinBox,
                             QTabWidget, QListWidget, QListWidgetItem, QFileDialog, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap
import sys
import os
from pathlib import Path
from datetime import date, datetime
from views.base_crud_view import BaseCRUDView
from views.configuracion_alquiler_window import ConfiguracionAlquilerDialog
from models.database_model import (obtener_session, Alquiler, AlquilerDetalle,
                                   EstadoAlquiler, EstadoEquipo, TipoEquipo,
                                   Equipo, Cliente, AlquilerEvidencia)
from utils.file_manager import FileManager
from utils.widgets import SearchableComboBox, UpperLineEdit

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
            detalles.append({
                'equipo_id': equipo_id,
                'cantidad': 1,
                'tarifa': equipo.tarifa_diaria_referencial
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

class AlquilerDialog(QDialog):
    """Diálogo para crear/editar Alquiler"""
    alquiler_guardado = pyqtSignal()

    def __init__(self, parent=None, alquiler=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.alquiler = alquiler
        self.detalles_temp = [] # Lista de dicts
        self.init_ui()
        
        if alquiler:
            self.cargar_datos()

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
        
        toolbar_det.addWidget(btn_add_kit)
        toolbar_det.addWidget(btn_add_item)
        toolbar_det.addStretch()
        
        det_layout.addLayout(toolbar_det)
        
        self.tabla_detalles = QTableWidget()
        self.tabla_detalles.setColumnCount(5)
        self.tabla_detalles.setHorizontalHeaderLabels(["Código", "Descripción", "Cant.", "Tarifa/Precio", "Subtotal"])
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
        # TODO: Diálogo simple para seleccionar 1 equipo
        QMessageBox.information(self, "Info", "Funcionalidad simplificada: Use 'Agregar Kit' por ahora para probar la lógica compleja.")

    def actualizar_tabla_detalles(self):
        self.tabla_detalles.setRowCount(0)
        total = 0.0
        for det in self.detalles_temp:
            row = self.tabla_detalles.rowCount()
            self.tabla_detalles.insertRow(row)
            
            equipo = self.session.query(Equipo).get(det['equipo_id'])
            
            self.tabla_detalles.setItem(row, 0, QTableWidgetItem(equipo.codigo))
            self.tabla_detalles.setItem(row, 1, QTableWidgetItem(equipo.nombre))
            self.tabla_detalles.setItem(row, 2, QTableWidgetItem(str(det['cantidad'])))
            self.tabla_detalles.setItem(row, 3, QTableWidgetItem(f"{det['tarifa']:.2f}"))
            
            subtotal = det['cantidad'] * det['tarifa']
            self.tabla_detalles.setItem(row, 4, QTableWidgetItem(f"{subtotal:.2f}"))
            total += subtotal

    def cargar_datos(self):
        if not self.alquiler: return
        
        self.date_inicio.setDate(self.alquiler.fecha_inicio)
        if self.alquiler.fecha_fin_estimada:
            self.date_fin.setDate(self.alquiler.fecha_fin_estimada)
            
        index = self.cmb_cliente.findData(self.alquiler.cliente_id)
        if index >= 0: self.cmb_cliente.setCurrentIndex(index)
        
        self.txt_obra.setText(self.alquiler.ubicacion_obra or "")
        
        # Cargar detalles (simplificado: solo lectura por ahora en esta vista rápida)
        # TODO: Implementar carga completa de detalles para edición
        
        self.cargar_evidencias()

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
                for det in self.detalles_temp:
                    nuevo_det = AlquilerDetalle(
                        alquiler_id=self.alquiler.id,
                        equipo_id=det['equipo_id'],
                        cantidad=det['cantidad'],
                        tarifa_diaria=det['tarifa']
                    )
                    self.session.add(nuevo_det)
                    
                    # Actualizar estado del equipo
                    equipo = self.session.query(Equipo).get(det['equipo_id'])
                    equipo.estado = EstadoEquipo.ALQUILADO
            
            self.session.commit()
            self.alquiler_guardado.emit()
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class AlquileresWindow(BaseCRUDView):
    """Ventana de gestión de Alquileres"""
    
    def __init__(self):
        super().__init__("Gestión de Alquileres", Alquiler, AlquilerDialog)
        self.agregar_boton_configuracion()

    def agregar_boton_configuracion(self):
        # Intentar obtener el layout del header (primer item del main layout)
        try:
            header_layout = self.layout().itemAt(0).layout()
            if header_layout:
                self.btn_config = QPushButton("⚙️ Configuración")
                self.btn_config.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 6px 12px;")
                self.btn_config.clicked.connect(self.abrir_configuracion)
                
                # Insertar antes del botón "Nuevo" (que es el último widget)
                # O simplemente agregar al layout, aparecerá al lado
                header_layout.insertWidget(header_layout.count() - 1, self.btn_config)
        except Exception as e:
            print(f"Error al agregar botón configuración: {e}")

    def abrir_configuracion(self):
        dialog = ConfiguracionAlquilerDialog(self)
        dialog.exec()
        
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
