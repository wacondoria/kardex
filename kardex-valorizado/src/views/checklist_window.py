from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QDialog,
                             QFormLayout, QLineEdit, QComboBox, QCheckBox, QMessageBox,
                             QHeaderView, QGroupBox, QRadioButton, QTextEdit, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from models.database_model import (obtener_session, ChecklistModel, ChecklistItem, 
                                   TipoEquipo, ChecklistInstancia, ChecklistInstanciaDetalle,
                                   Usuario)
from datetime import datetime

class ChecklistManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.session = obtener_session()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Gestión de Modelos de Checklist")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        
        btn_new = QPushButton("➕ Nuevo Modelo")
        btn_new.clicked.connect(self.open_new_dialog)
        header_layout.addWidget(btn_new)
        
        layout.addLayout(header_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Tipo de Equipo", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

    def load_data(self):
        self.table.setRowCount(0)
        modelos = self.session.query(ChecklistModel).filter(ChecklistModel.activo == True).all()
        
        for row, modelo in enumerate(modelos):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(modelo.id)))
            self.table.setItem(row, 1, QTableWidgetItem(modelo.nombre))
            
            tipo_nombre = "General"
            if modelo.tipo_equipo_id:
                tipo = self.session.query(TipoEquipo).get(modelo.tipo_equipo_id)
                if tipo:
                    tipo_nombre = tipo.nombre
            self.table.setItem(row, 2, QTableWidgetItem(tipo_nombre))
            
            btn_edit = QPushButton("✏️ Editar")
            btn_edit.clicked.connect(lambda _, m=modelo: self.open_edit_dialog(m))
            self.table.setCellWidget(row, 3, btn_edit)

    def open_new_dialog(self):
        dialog = ChecklistModelDialog(self.session)
        if dialog.exec():
            self.load_data()

    def open_edit_dialog(self, modelo):
        dialog = ChecklistModelDialog(self.session, modelo)
        if dialog.exec():
            self.load_data()
            
    def closeEvent(self, event):
        self.session.close()
        super().closeEvent(event)

class ChecklistModelDialog(QDialog):
    def __init__(self, session, modelo=None):
        super().__init__()
        self.session = session
        self.modelo = modelo
        self.setWindowTitle("Modelo de Checklist")
        self.resize(600, 500)
        self.init_ui()
        if modelo:
            self.load_modelo()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.txt_nombre = QLineEdit()
        self.cmb_tipo = QComboBox()
        
        # Load Tipos
        tipos = self.session.query(TipoEquipo).all()
        self.cmb_tipo.addItem("General (Todos)", None)
        for t in tipos:
            self.cmb_tipo.addItem(t.nombre, t.id)
            
        form.addRow("Nombre:", self.txt_nombre)
        form.addRow("Tipo de Equipo:", self.cmb_tipo)
        layout.addLayout(form)
        
        # Items
        layout.addWidget(QLabel("Items del Checklist:"))
        self.items_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.items_widget = QWidget()
        self.items_widget.setLayout(self.items_layout)
        scroll.setWidget(self.items_widget)
        layout.addWidget(scroll)
        
        btn_add_item = QPushButton("➕ Agregar Item")
        btn_add_item.clicked.connect(self.add_item_row)
        layout.addWidget(btn_add_item)
        
        # Buttons
        btns = QHBoxLayout()
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_save)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)
        
        self.item_rows = []

    def add_item_row(self, item_obj=None):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        txt_desc = QLineEdit()
        txt_desc.setPlaceholderText("Descripción del item (ej: Nivel de Aceite)")
        chk_critico = QCheckBox("Crítico")
        btn_remove = QPushButton("❌")
        btn_remove.clicked.connect(lambda: self.remove_item_row(row_widget))
        
        if item_obj:
            txt_desc.setText(item_obj.descripcion)
            chk_critico.setChecked(item_obj.es_critico)
            
        row_layout.addWidget(txt_desc)
        row_layout.addWidget(chk_critico)
        row_layout.addWidget(btn_remove)
        
        self.items_layout.addWidget(row_widget)
        self.item_rows.append({
            "widget": row_widget,
            "txt": txt_desc,
            "chk": chk_critico,
            "obj": item_obj
        })

    def remove_item_row(self, widget):
        widget.deleteLater()
        self.item_rows = [r for r in self.item_rows if r["widget"] != widget]

    def load_modelo(self):
        self.txt_nombre.setText(self.modelo.nombre)
        index = self.cmb_tipo.findData(self.modelo.tipo_equipo_id)
        if index >= 0:
            self.cmb_tipo.setCurrentIndex(index)
            
        for item in self.modelo.items:
            self.add_item_row(item)

    def save(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio")
            return
            
        tipo_id = self.cmb_tipo.currentData()
        
        if not self.modelo:
            self.modelo = ChecklistModel(nombre=nombre, tipo_equipo_id=tipo_id)
            self.session.add(self.modelo)
            self.session.flush() # Get ID
        else:
            self.modelo.nombre = nombre
            self.modelo.tipo_equipo_id = tipo_id
            
        # Update items
        # Simple strategy: delete all existing and re-create (or update in place if complex)
        # Here we will mark existing as to-keep or delete
        
        current_items = {item.id: item for item in self.modelo.items}
        seen_ids = set()
        
        for i, row in enumerate(self.item_rows):
            desc = row["txt"].text().strip()
            critico = row["chk"].isChecked()
            
            if not desc: continue
            
            item_obj = row["obj"]
            if item_obj:
                item_obj.descripcion = desc
                item_obj.es_critico = critico
                item_obj.orden = i
                seen_ids.add(item_obj.id)
            else:
                new_item = ChecklistItem(
                    modelo_id=self.modelo.id,
                    descripcion=desc,
                    es_critico=critico,
                    orden=i
                )
                self.session.add(new_item)
                
        # Delete removed items
        for i_id, item in current_items.items():
            if i_id not in seen_ids:
                self.session.delete(item)
                
        try:
            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class ChecklistFillDialog(QDialog):
    def __init__(self, session, equipo, usuario_id, parent=None):
        super().__init__(parent)
        self.session = session
        self.equipo = equipo
        self.usuario_id = usuario_id
        self.setWindowTitle(f"Realizar Checklist - {equipo.nombre}")
        self.resize(700, 600)
        
        self.init_ui()
        self.load_template()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header Info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"<b>Equipo:</b> {self.equipo.codigo} - {self.equipo.nombre}"))
        info_layout.addWidget(QLabel(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}"))
        layout.addLayout(info_layout)
        
        form = QFormLayout()
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems(["SALIDA", "RETORNO", "MANTENIMIENTO"])
        form.addRow("Tipo de Checklist:", self.cmb_tipo)
        layout.addLayout(form)
        
        # Items Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.items_widget = QWidget()
        self.items_layout = QVBoxLayout(self.items_widget)
        scroll.setWidget(self.items_widget)
        layout.addWidget(scroll)
        
        # Global Observations
        layout.addWidget(QLabel("Observaciones Generales:"))
        self.txt_obs_general = QTextEdit()
        self.txt_obs_general.setMaximumHeight(80)
        layout.addWidget(self.txt_obs_general)
        
        # Buttons
        btns = QHBoxLayout()
        btn_save = QPushButton("💾 Guardar Checklist")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_save)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)
        
        self.input_rows = []

    def load_template(self):
        # Find model for this equipment type
        modelo = self.session.query(ChecklistModel).filter(
            ChecklistModel.tipo_equipo_id == self.equipo.tipo_equipo_id,
            ChecklistModel.activo == True
        ).first()
        
        if not modelo:
            # Try general model
            modelo = self.session.query(ChecklistModel).filter(
                ChecklistModel.tipo_equipo_id == None,
                ChecklistModel.activo == True
            ).first()
            
        if not modelo:
            QMessageBox.warning(self, "Aviso", "No hay un modelo de checklist configurado para este tipo de equipo.")
            self.reject()
            return
            
        # Render items
        for item in modelo.items:
            self.add_item_input(item)

    def add_item_input(self, item):
        group = QGroupBox(item.descripcion)
        if item.es_critico:
            group.setTitle(f"{item.descripcion} (CRÍTICO)")
            group.setStyleSheet("QGroupBox { font-weight: bold; color: #c0392b; }")
            
        layout = QVBoxLayout(group)
        
        # Status Radios
        radio_layout = QHBoxLayout()
        r_ok = QRadioButton("OK")
        r_bad = QRadioButton("MALO")
        r_na = QRadioButton("N/A")
        r_ok.setChecked(True)
        
        radio_layout.addWidget(r_ok)
        radio_layout.addWidget(r_bad)
        radio_layout.addWidget(r_na)
        radio_layout.addStretch()
        layout.addLayout(radio_layout)
        
        # Observation
        txt_obs = QLineEdit()
        txt_obs.setPlaceholderText("Observación...")
        layout.addWidget(txt_obs)
        
        self.items_layout.addWidget(group)
        
        self.input_rows.append({
            "item": item,
            "radios": (r_ok, r_bad, r_na),
            "obs": txt_obs
        })

    def save(self):
        # Validation
        aprobado = True
        
        instancia = ChecklistInstancia(
            equipo_id=self.equipo.id,
            usuario_id=self.usuario_id,
            tipo=self.cmb_tipo.currentText(),
            observaciones=self.txt_obs_general.toPlainText()
        )
        self.session.add(instancia)
        self.session.flush()
        
        for row in self.input_rows:
            r_ok, r_bad, r_na = row["radios"]
            estado = "OK"
            if r_bad.isChecked(): estado = "MALO"
            elif r_na.isChecked(): estado = "NO_APLICA"
            
            if estado == "MALO":
                aprobado = False
            
            detalle = ChecklistInstanciaDetalle(
                instancia_id=instancia.id,
                item_descripcion=row["item"].descripcion,
                estado=estado,
                observacion=row["obs"].text()
            )
            self.session.add(detalle)
            
        instancia.aprobado = aprobado
        
        try:
            self.session.commit()
            msg = "Checklist guardado correctamente."
            if not aprobado:
                msg += "\n\n⚠️ ATENCIÓN: El checklist fue RECHAZADO debido a items en mal estado."
            QMessageBox.information(self, "Éxito", msg)
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))
