from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidgetItem, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QMessageBox,
                             QComboBox, QCheckBox, QDateEdit, QDoubleSpinBox, QTextEdit, QFileDialog, QTabWidget, QGridLayout, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSize, QRegularExpression
from PyQt6.QtGui import QFont, QPixmap, QRegularExpressionValidator
import sys
import os
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Equipo, Almacen, NivelEquipo, EstadoEquipo, TipoEquipo
from utils.widgets import SearchableComboBox, UpperLineEdit
from utils.file_manager import FileManager
from views.base_crud_view import BaseCRUDView

def generar_codigo_equipo(session, prefijo):
    """Genera el código completo con numeración automática para equipos"""
    # Buscar el último código que empiece con el prefijo
    ultimo = session.query(Equipo).filter(
        Equipo.codigo.like(f"{prefijo}-%")
    ).order_by(Equipo.codigo.desc()).first()

    if ultimo:
        try:
            numero = int(ultimo.codigo.split('-')[1]) + 1
        except IndexError:
            numero = 1
    else:
        numero = 1

    return f"{prefijo}-{numero:06d}"

class EquipoDialog(QDialog):
    """Diálogo para crear/editar equipos"""
    
    equipo_guardado = pyqtSignal()

    def __init__(self, parent=None, equipo=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.equipo = equipo
        self.ruta_foto_actual = None
        self.init_ui()
        
        if self.equipo:
            self.cargar_datos()
        else:
            self.cmb_codigo.setCurrentIndex(-1)
        
    def init_ui(self):
        self.setWindowTitle("Nuevo Equipo" if not self.equipo else "Editar Equipo")
        self.setFixedSize(800, 700)
        
        main_layout = QVBoxLayout()
        
        # --- TABS ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # === TAB 1: GENERAL ===
        tab_general = QWidget()
        layout_general = QVBoxLayout()
        
        # 1. Identificación
        grp_ident = QGroupBox("Identificación")
        form_ident = QFormLayout()
        
        # --- CÓDIGO PREFIJO ---
        codigo_layout = QHBoxLayout()
        self.cmb_codigo = SearchableComboBox()
        self.cmb_codigo.setPlaceholderText("Ej: GENER")
        self.cmb_codigo.setToolTip("Escriba un prefijo de 5 letras")
        
        validator = QRegularExpressionValidator(QRegularExpression("[A-Z0-9]{5}"))
        self.cmb_codigo.lineEdit().setValidator(validator)
        self.cmb_codigo.lineEdit().textChanged.connect(lambda text: self.cmb_codigo.lineEdit().setText(text.upper()))
        
        self.cmb_codigo.currentTextChanged.connect(self.actualizar_siguiente_correlativo)
        
        self.lbl_codigo_completo = QLabel("-...")
        self.lbl_codigo_completo.setStyleSheet("color: #666; font-weight: bold;")
        
        codigo_layout.addWidget(self.cmb_codigo)
        codigo_layout.addWidget(self.lbl_codigo_completo)
        codigo_layout.addStretch()
        
        # Nombre (Auto-generado pero editable)
        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Se autocompletará...")
        
        form_ident.addRow("Código (Prefijo):*", codigo_layout)
        form_ident.addRow("Nombre:*", self.txt_nombre)
        
        # Tipo y Capacidad
        self.cmb_tipo = SearchableComboBox()
        self.cmb_tipo.currentIndexChanged.connect(self.actualizar_nombre)
        self.cargar_tipos_equipo()
        
        self.txt_capacidad = QLineEdit()
        self.txt_capacidad.setPlaceholderText("Ej: 5000W, 300KG")
        self.txt_capacidad.textChanged.connect(self.actualizar_nombre)
        
        form_ident.addRow("Tipo de Equipo:", self.cmb_tipo)
        form_ident.addRow("Capacidad:", self.txt_capacidad)
        
        grp_ident.setLayout(form_ident)
        layout_general.addWidget(grp_ident)
        
        # 2. Ubicación y Estado
        grp_ubic = QGroupBox("Ubicación y Estado")
        form_ubic = QFormLayout()
        
        self.cmb_nivel = QComboBox()
        for nivel in NivelEquipo:
            self.cmb_nivel.addItem(nivel.value, nivel)
            
        self.cmb_almacen = SearchableComboBox()
        self.cargar_almacenes()
        
        form_ubic.addRow("Nivel Jerarquía:*", self.cmb_nivel)
        form_ubic.addRow("Ubicación Actual:", self.cmb_almacen)
        grp_ubic.setLayout(form_ubic)
        layout_general.addWidget(grp_ubic)
        
        # 3. Descripción
        layout_general.addWidget(QLabel("Descripción:"))
        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(60)
        layout_general.addWidget(self.txt_descripcion)

        # 4. Foto Referencial
        grp_foto = QGroupBox("Foto Referencial")
        layout_foto = QHBoxLayout()
        
        self.lbl_foto = QLabel("Sin imagen")
        self.lbl_foto.setFixedSize(100, 100)
        self.lbl_foto.setScaledContents(True)
        self.lbl_foto.setStyleSheet("border: 1px dashed #ccc; background-color: #eee;")
        
        btn_cargar_foto = QPushButton("Cargar Multimedia")
        btn_cargar_foto.clicked.connect(self.cargar_foto)
        
        layout_foto.addWidget(self.lbl_foto)
        layout_foto.addWidget(btn_cargar_foto)
        layout_foto.addStretch()
        
        grp_foto.setLayout(layout_foto)
        layout_general.addWidget(grp_foto)
        
        tab_general.setLayout(layout_general)
        self.tabs.addTab(tab_general, "General")
        
        # === TAB 2: DETALLES TÉCNICOS ===
        tab_tecnico = QWidget()
        layout_tecnico = QVBoxLayout()
        
        # 1. Datos Técnicos
        grp_tec = QGroupBox("Datos Técnicos")
        form_tec = QFormLayout()
        self.txt_marca = UpperLineEdit()
        self.txt_marca.textChanged.connect(self.actualizar_nombre)
        
        self.txt_modelo = UpperLineEdit()
        self.txt_modelo.textChanged.connect(self.actualizar_nombre)
        
        self.txt_serie_modelo = UpperLineEdit()
        self.txt_serie_modelo.textChanged.connect(self.actualizar_nombre)
        
        self.txt_serie = UpperLineEdit()
        self.txt_serie.textChanged.connect(self.actualizar_nombre)
        
        form_tec.addRow("Marca:", self.txt_marca)
        form_tec.addRow("Modelo:", self.txt_modelo)
        form_tec.addRow("Serie del Modelo:", self.txt_serie_modelo)
        form_tec.addRow("Serie (S/N):", self.txt_serie)
        grp_tec.setLayout(form_tec)
        layout_tecnico.addWidget(grp_tec)
        
        # 2. Control y Mantenimiento
        grp_mant = QGroupBox("Control y Mantenimiento")
        grid_mant = QGridLayout()
        
        self.chk_calibracion = QCheckBox("Requiere Calibración")
        self.chk_calibracion.toggled.connect(self.toggle_calibracion)
        
        # Fecha Última Calibración
        self.date_ultima_calibracion = QDateEdit(date.today())
        self.date_ultima_calibracion.setCalendarPopup(True)
        self.date_ultima_calibracion.setEnabled(False)
        
        # Fecha Vencimiento
        self.date_vencimiento = QDateEdit(date.today())
        self.date_vencimiento.setCalendarPopup(True)
        self.date_vencimiento.setEnabled(False)
        self.date_vencimiento.dateChanged.connect(self.calcular_dias_vencidos)
        
        self.lbl_dias_vencidos = QLabel("")
        self.lbl_dias_vencidos.setStyleSheet("color: red; font-weight: bold;")
        
        grid_mant.addWidget(self.chk_calibracion, 0, 0)
        
        grid_mant.addWidget(QLabel("Última Calibración:"), 1, 0)
        grid_mant.addWidget(self.date_ultima_calibracion, 1, 1)
        
        grid_mant.addWidget(QLabel("Vencimiento:"), 2, 0)
        grid_mant.addWidget(self.date_vencimiento, 2, 1)
        grid_mant.addWidget(self.lbl_dias_vencidos, 2, 2)
        
        self.chk_horometro = QCheckBox("Control por Horómetro")
        self.chk_horometro.toggled.connect(self.toggle_horometro)
        self.spn_horometro = QDoubleSpinBox()
        self.spn_horometro.setRange(0, 999999)
        self.spn_horometro.setSuffix(" Hrs")
        self.spn_horometro.setEnabled(False)
        
        grid_mant.addWidget(self.chk_horometro, 3, 0)
        grid_mant.addWidget(QLabel("Actual:"), 3, 1)
        grid_mant.addWidget(self.spn_horometro, 3, 2)
        
        grp_mant.setLayout(grid_mant)
        layout_tecnico.addWidget(grp_mant)
        
        # 3. Datos Financieros
        grp_fin = QGroupBox("Datos Financieros")
        form_fin = QFormLayout()
        
        self.spn_tarifa = QDoubleSpinBox()
        self.spn_tarifa.setRange(0, 999999)
        self.spn_tarifa.setPrefix("S/ ")
        
        self.spn_tarifa_dolares = QDoubleSpinBox()
        self.spn_tarifa_dolares.setRange(0, 999999)
        self.spn_tarifa_dolares.setPrefix("$ ")
        
        form_fin.addRow("Tarifa Diaria (S/):", self.spn_tarifa)
        form_fin.addRow("Tarifa Diaria ($):", self.spn_tarifa_dolares)
        
        grp_fin.setLayout(form_fin)
        layout_tecnico.addWidget(grp_fin)
        
        layout_tecnico.addStretch()
        tab_tecnico.setLayout(layout_tecnico)
        self.tabs.addTab(tab_tecnico, "Detalles Técnicos")
        
        # --- FOOTER ---
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.guardar)
        btn_save.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        
        main_layout.addLayout(btn_box)
        self.setLayout(main_layout)

    def cargar_almacenes(self):
        almacenes = self.session.query(Almacen).filter_by(activo=True).all()
        for alm in almacenes:
            self.cmb_almacen.addItem(alm.nombre, alm.id)

    def cargar_tipos_equipo(self):
        tipos = self.session.query(TipoEquipo).filter_by(activo=True).all()
        for t in tipos:
            self.cmb_tipo.addItem(t.nombre, t.id)
            
        # Cargar prefijos existentes también
        self.cargar_prefijos_existentes()

    def cargar_prefijos_existentes(self):
        try:
            codigos_tuplas = self.session.query(Equipo.codigo).distinct().all()
            prefijos_set = set()
            for (codigo,) in codigos_tuplas:
                if codigo and '-' in codigo:
                    prefijo = codigo.split('-')[0]
                    if len(prefijo) == 5:
                        prefijos_set.add(prefijo)
            
            prefijos_ordenados = sorted(list(prefijos_set))
            self.cmb_codigo.addItems(prefijos_ordenados)
        except Exception as e:
            print(f"Error al cargar prefijos: {e}")

    def actualizar_siguiente_correlativo(self, prefijo):
        if not self.cmb_codigo.isEnabled():
            return
            
        prefijo = prefijo.strip().upper()
        if len(prefijo) != 5:
            self.lbl_codigo_completo.setText("-(inválido)")
            return
            
        try:
            codigo_completo = generar_codigo_equipo(self.session, prefijo)
            sufijo = codigo_completo.split('-')[1]
            self.lbl_codigo_completo.setText(f"-{sufijo}")
        except Exception as e:
            print(f"Error al actualizar correlativo: {e}")

    def actualizar_nombre(self):
        """Autogenera el nombre del equipo"""
        if not hasattr(self, 'txt_capacidad') or not hasattr(self, 'txt_marca'):
            return

        tipo = self.cmb_tipo.currentText()
        capacidad = self.txt_capacidad.text().strip()
        marca = self.txt_marca.text().strip()
        modelo = self.txt_modelo.text().strip()
        serie_modelo = self.txt_serie_modelo.text().strip()
        serie = self.txt_serie.text().strip()
        
        partes = [tipo]
        if capacidad: partes.append(capacidad)
        if marca: partes.append(marca)
        if modelo: partes.append(modelo)
        if serie_modelo: partes.append(serie_modelo)
        if serie: partes.append(f"SN:{serie}")
        
        nombre_generado = " ".join(partes)
        self.txt_nombre.setText(nombre_generado.upper())

    def toggle_calibracion(self, checked):
        self.date_ultima_calibracion.setEnabled(checked)
        self.date_vencimiento.setEnabled(checked)
        if not checked:
            self.lbl_dias_vencidos.setText("")
        else:
            self.calcular_dias_vencidos()

    def calcular_dias_vencidos(self):
        if not self.chk_calibracion.isChecked():
            return
            
        fecha_venc = self.date_vencimiento.date().toPyDate()
        hoy = date.today()
        
        dias = (fecha_venc - hoy).days
        
        if dias < 0:
            self.lbl_dias_vencidos.setText(f"¡VENCIDO hace {abs(dias)} días!")
        elif dias < 30:
            self.lbl_dias_vencidos.setText(f"Vence en {dias} días")
            self.lbl_dias_vencidos.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.lbl_dias_vencidos.setText("")

    def toggle_horometro(self, checked):
        self.spn_horometro.setEnabled(checked)

    def cargar_datos(self):
        # Código
        if '-' in self.equipo.codigo:
            prefijo = self.equipo.codigo.split('-')[0]
            sufijo = self.equipo.codigo.split('-')[1]
            self.cmb_codigo.setCurrentText(prefijo)
            self.lbl_codigo_completo.setText(f"-{sufijo}")
        else:
            self.cmb_codigo.setCurrentText(self.equipo.codigo)
            
        self.cmb_codigo.setEnabled(False) # No editar código
        
        self.txt_nombre.setText(self.equipo.nombre)
        self.txt_descripcion.setPlainText(self.equipo.descripcion or "")
        
        index = self.cmb_nivel.findData(self.equipo.nivel)
        if index >= 0: self.cmb_nivel.setCurrentIndex(index)
        
        index_alm = self.cmb_almacen.findData(self.equipo.almacen_id)
        if index_alm >= 0: self.cmb_almacen.setCurrentIndex(index_alm)
        
        # Tipo y Capacidad
        index_tipo = self.cmb_tipo.findData(self.equipo.tipo_equipo_id)
        if index_tipo >= 0: self.cmb_tipo.setCurrentIndex(index_tipo)
        
        self.txt_capacidad.setText(self.equipo.capacidad or "")
        
        self.txt_marca.setText(self.equipo.marca or "")
        self.txt_modelo.setText(self.equipo.modelo or "")
        self.txt_serie_modelo.setText(self.equipo.serie_modelo or "")
        self.txt_serie.setText(self.equipo.serie or "")
        
        self.chk_calibracion.setChecked(self.equipo.requiere_calibracion)
        if self.equipo.fecha_ultima_calibracion:
            self.date_ultima_calibracion.setDate(self.equipo.fecha_ultima_calibracion)
        if self.equipo.fecha_vencimiento_calibracion:
            self.date_vencimiento.setDate(self.equipo.fecha_vencimiento_calibracion)
            self.calcular_dias_vencidos()
            
        self.chk_horometro.setChecked(self.equipo.control_horometro)
        self.spn_horometro.setValue(self.equipo.horometro_actual)
        
        self.spn_tarifa.setValue(self.equipo.tarifa_diaria_referencial)
        self.spn_tarifa_dolares.setValue(self.equipo.tarifa_diaria_dolares or 0.0)

        if self.equipo.foto_referencia:
            self.mostrar_multimedia(self.equipo.foto_referencia)
            self.ruta_foto_actual = self.equipo.foto_referencia

    def cargar_foto(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Seleccionar Multimedia", "", "Imágenes y Videos (*.png *.jpg *.jpeg *.mp4 *.avi *.mov)")
        if file_name:
            self.mostrar_multimedia(file_name)
            self.ruta_foto_actual = file_name

    def mostrar_multimedia(self, path):
        # Si es ruta relativa, obtener absoluta
        full_path = FileManager.get_full_path(path) if not os.path.isabs(path) else path
        
        if not full_path or not os.path.exists(full_path):
            self.lbl_foto.setText("No encontrado")
            return

        if FileManager.is_video(full_path):
            self.lbl_foto.setText("🎥 VIDEO")
            self.lbl_foto.setStyleSheet("border: 1px solid blue; color: blue; font-weight: bold; font-size: 16px;")
        else:
            pixmap = QPixmap(full_path)
            self.lbl_foto.setPixmap(pixmap)
            self.lbl_foto.setStyleSheet("border: 1px dashed #ccc; background-color: #eee;")

    def guardar(self):
        prefijo = self.cmb_codigo.currentText().strip().upper()
        nombre = self.txt_nombre.text().strip()
        
        if len(prefijo) != 5:
            QMessageBox.warning(self, "Error", "El prefijo del código debe tener 5 caracteres.")
            return
            
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
            return
            
        try:
            if not self.equipo:
                # Nuevo
                codigo_completo = generar_codigo_equipo(self.session, prefijo)
                
                existe = self.session.query(Equipo).filter_by(codigo=codigo_completo).first()
                if existe:
                    QMessageBox.warning(self, "Error", "El código generado ya existe. Intente de nuevo.")
                    self.actualizar_siguiente_correlativo(prefijo)
                    return
                
                self.equipo = Equipo(codigo=codigo_completo)
                self.session.add(self.equipo)
            
            self.equipo.nombre = nombre
            self.equipo.descripcion = self.txt_descripcion.toPlainText()
            self.equipo.nivel = self.cmb_nivel.currentData()
            self.equipo.almacen_id = self.cmb_almacen.currentData()
            
            self.equipo.tipo_equipo_id = self.cmb_tipo.currentData()
            self.equipo.capacidad = self.txt_capacidad.text()
            
            self.equipo.marca = self.txt_marca.text()
            self.equipo.modelo = self.txt_modelo.text()
            self.equipo.serie_modelo = self.txt_serie_modelo.text()
            self.equipo.serie = self.txt_serie.text()
            
            self.equipo.requiere_calibracion = self.chk_calibracion.isChecked()
            if self.chk_calibracion.isChecked():
                self.equipo.fecha_ultima_calibracion = self.date_ultima_calibracion.date().toPyDate()
                self.equipo.fecha_vencimiento_calibracion = self.date_vencimiento.date().toPyDate()
            else:
                self.equipo.fecha_ultima_calibracion = None
                self.equipo.fecha_vencimiento_calibracion = None
                
            self.equipo.control_horometro = self.chk_horometro.isChecked()
            self.equipo.horometro_actual = self.spn_horometro.value()
            
            self.equipo.tarifa_diaria_referencial = self.spn_tarifa.value()
            self.equipo.tarifa_diaria_dolares = self.spn_tarifa_dolares.value()
            
            # Guardar Foto/Video
            if self.ruta_foto_actual and self.ruta_foto_actual != self.equipo.foto_referencia:
                # Si es una ruta nueva (no la que ya tenía guardada)
                if os.path.isabs(self.ruta_foto_actual):
                    nueva_ruta = FileManager.save_file(self.ruta_foto_actual, "detalle_equipos")
                    self.equipo.foto_referencia = nueva_ruta
            
            self.session.commit()
            self.equipo_guardado.emit()
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}")

class EquiposWindow(BaseCRUDView):
    """Ventana de gestión de Equipos"""
    
    def __init__(self):
        super().__init__("Gestión de Equipos", Equipo, EquipoDialog)
        
    def setup_table_columns(self):
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "Código", "Nombre", "Tipo", "Capacidad", "Estado", "Ubicación", "Venc. Calib.", "Acciones"
        ])
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
    def fill_row(self, row, item):
        self.tabla.setItem(row, 0, QTableWidgetItem(item.codigo))
        self.tabla.setItem(row, 1, QTableWidgetItem(item.nombre))
        
        tipo_nombre = item.tipo_equipo.nombre if item.tipo_equipo else "N/A"
        self.tabla.setItem(row, 2, QTableWidgetItem(tipo_nombre))
        
        self.tabla.setItem(row, 3, QTableWidgetItem(item.capacidad or ""))
        
        # Estado con color
        estado_item = QTableWidgetItem(item.estado.value)
        if item.estado == EstadoEquipo.DISPONIBLE:
            estado_item.setForeground(Qt.GlobalColor.darkGreen)
        elif item.estado == EstadoEquipo.MANTENIMIENTO:
            estado_item.setForeground(Qt.GlobalColor.darkRed)
        self.tabla.setItem(row, 4, estado_item)
        
        ubicacion = item.almacen.nombre if item.almacen else "Sin asignar"
        self.tabla.setItem(row, 5, QTableWidgetItem(ubicacion))
        
        venc = ""
        if item.requiere_calibracion and item.fecha_vencimiento_calibracion:
            venc = item.fecha_vencimiento_calibracion.strftime("%d/%m/%Y")
            # Semáforo
            dias = (item.fecha_vencimiento_calibracion - date.today()).days
            
            if dias < 0:
                venc += f" ({abs(dias)} días vencido)"
                venc_item = QTableWidgetItem(venc)
                venc_item.setBackground(Qt.GlobalColor.red)
                venc_item.setForeground(Qt.GlobalColor.white)
            elif dias < 30:
                venc_item = QTableWidgetItem(venc)
                venc_item.setBackground(Qt.GlobalColor.yellow)
                venc_item.setForeground(Qt.GlobalColor.black)
            else:
                venc_item = QTableWidgetItem(venc)
                
            self.tabla.setItem(row, 6, venc_item)
        else:
            self.tabla.setItem(row, 6, QTableWidgetItem("N/A"))

    def _open_dialog(self, item=None):
        dialog = EquipoDialog(self, equipo=item)
        dialog.equipo_guardado.connect(self.load_data)
        dialog.exec()
