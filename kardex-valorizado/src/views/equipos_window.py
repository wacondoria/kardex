from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidgetItem, QDialog,
                             QFormLayout, QHeaderView, QGroupBox, QMessageBox,
                             QComboBox, QCheckBox, QDateEdit, QDoubleSpinBox, QTextEdit, QFileDialog, QTabWidget, QGridLayout, QLineEdit, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSize, QRegularExpression
from PyQt6.QtGui import QFont, QPixmap, QRegularExpressionValidator
import sys
import os
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Equipo, Almacen, NivelEquipo, EstadoEquipo, TipoEquipo, SubtipoEquipo, Proveedor
from utils.widgets import SearchableComboBox, UpperLineEdit
from utils.file_manager import FileManager
from views.base_crud_view import BaseCRUDView
from utils.styles import STYLE_CUADRADO_VERDE, STYLE_CHECKBOX_CUSTOM

# Try import ProveedorDialog from proveedores_window
try:
    from views.proveedores_window import ProveedorDialog
except ImportError:
    ProveedorDialog = None

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

def generar_codigo_unico_global(session):
    """Genera un código único global correlativo (Ej: EQ00001)"""
    # Buscar el último código único que empiece con EQ
    ultimo = session.query(Equipo).filter(
        Equipo.codigo_unico.like("EQ%")
    ).order_by(Equipo.codigo_unico.desc()).first()

    if ultimo and ultimo.codigo_unico:
        try:
            numero = int(ultimo.codigo_unico.replace("EQ", "")) + 1
        except ValueError:
            numero = 1
    else:
        numero = 1

    return f"EQ{numero:05d}"

class TipoEquipoDialog(QDialog):
    """Diálogo para crear o editar un Tipo de Equipo"""
    tipo_guardado = pyqtSignal()

    def __init__(self, parent=None, tipo_equipo=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.tipo_equipo = tipo_equipo
        self.init_ui()

        if self.tipo_equipo:
            self.cargar_datos()

    def init_ui(self):
        self.setWindowTitle("Nuevo Tipo de Equipo" if not self.tipo_equipo else "Editar Tipo de Equipo")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.txt_nombre = UpperLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: GRUPO ELECTROGENO")
        form.addRow("Nombre:*", self.txt_nombre)

        self.txt_desc = QLineEdit()
        form.addRow("Descripción:", self.txt_desc)

        layout.addLayout(form)

        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.guardar)
        layout.addWidget(btn_save)

        self.setLayout(layout)

    def cargar_datos(self):
        self.txt_nombre.setText(self.tipo_equipo.nombre)
        self.txt_desc.setText(self.tipo_equipo.descripcion or "")

    def guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
            return

        try:
            if self.tipo_equipo:
                # Editar existente
                tipo = self.session.get(TipoEquipo, self.tipo_equipo.id)
                if tipo:
                    tipo.nombre = nombre
                    tipo.descripcion = self.txt_desc.text()
                else:
                    QMessageBox.warning(self, "Error", "No se encontró el tipo de equipo para editar.")
                    return
            else:
                # Nuevo
                nuevo_tipo = TipoEquipo(nombre=nombre, descripcion=self.txt_desc.text())
                self.session.add(nuevo_tipo)

            self.session.commit()
            self.tipo_guardado.emit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", str(e))

class SubtipoEquipoDialog(QDialog):
    """Diálogo para crear o editar un Subtipo de Equipo"""
    subtipo_guardado = pyqtSignal()

    def __init__(self, parent=None, subtipo=None, tipo_equipo_id=None):
        super().__init__(parent)
        self.session = obtener_session()
        self.subtipo = subtipo
        self.tipo_equipo_id = tipo_equipo_id
        self.init_ui()
        if self.subtipo:
            self.cargar_datos()
            # FIX: Asegurar que se guarde el subtipo correctamente
            subtipo_id = self.cmb_subtipo.currentData()
            
            # Si currentData es None, intentar buscar por texto exacto (case insensitive)
            if subtipo_id is None:
                text = self.cmb_subtipo.currentText().strip().upper()
                if text:
                    for i in range(self.cmb_subtipo.count()):
                        if self.cmb_subtipo.itemText(i).upper() == text:
                            subtipo_id = self.cmb_subtipo.itemData(i)
                            break
            
            # Si el texto está vacío, explícitamente None
            if not self.cmb_subtipo.currentText().strip():
                subtipo_id = None

            self.equipo.subtipo_equipo_id = subtipo_id
            self.equipo.capacidad = self.txt_capacidad.text()
            
            # self.equipo.proveedor_id = self.cmb_ruc_proveedor.currentData() # MOVIDO A MODULO ALQUILERES

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
        
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
    def setup_table_columns(self):
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "Cód. Único", "Código", "Nombre", "Tipo", "Capacidad", "Estado", "Ubicación", "Venc. Calib.", "Acciones"
        ])
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.setColumnWidth(0, 80) # Cód Único
        self.tabla.setColumnWidth(8, 180)
        
    def fill_row(self, row, item):
        self.tabla.setItem(row, 0, QTableWidgetItem(item.codigo_unico or "N/A"))
        self.tabla.setItem(row, 1, QTableWidgetItem(item.codigo))
        self.tabla.setItem(row, 2, QTableWidgetItem(item.nombre))
        
        tipo_nombre = item.tipo_equipo.nombre if item.tipo_equipo else "N/A"
        self.tabla.setItem(row, 3, QTableWidgetItem(tipo_nombre))
        
        self.tabla.setItem(row, 4, QTableWidgetItem(item.capacidad or ""))
        
        # Estado con color
        estado_item = QTableWidgetItem(item.estado.value)
        if item.estado == EstadoEquipo.DISPONIBLE:
            estado_item.setForeground(Qt.GlobalColor.darkGreen)
        elif item.estado == EstadoEquipo.MANTENIMIENTO:
            estado_item.setForeground(Qt.GlobalColor.darkRed)
        self.tabla.setItem(row, 5, estado_item)
        
        ubicacion = item.almacen.nombre if item.almacen else "Sin asignar"
        self.tabla.setItem(row, 6, QTableWidgetItem(ubicacion))
        
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
                
            self.tabla.setItem(row, 7, venc_item)
        else:
            self.tabla.setItem(row, 7, QTableWidgetItem("N/A"))

    def _open_dialog(self, item=None):
        dialog = EquipoDialog(self, equipo=item)
        dialog.equipo_guardado.connect(self.load_data)
        dialog.exec()

    def eliminar_equipo(self):
        """Elimina los equipos seleccionados."""
        selected_rows = sorted(set(index.row() for index in self.tabla.selectedIndexes()), reverse=True)
        
        if not selected_rows:
            QMessageBox.warning(self, "Aviso", "Seleccione al menos un equipo para eliminar.")
            return

        cantidad = len(selected_rows)
        msg = "¿Está seguro de eliminar el equipo seleccionado?" if cantidad == 1 else f"¿Está seguro de eliminar los {cantidad} equipos seleccionados?"
        
        confirm = QMessageBox.question(self, "Confirmar Eliminación", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                eliminados = 0
                errores = []
                
                for row in selected_rows:
                    # El código único está en la columna 0, el código normal en la 1
                    # Usamos el código normal para buscar por ahora, o el único si está disponible
                    codigo = self.tabla.item(row, 1).text() # Columna 1 es Código Original
                    equipo = self.session.query(Equipo).filter_by(codigo=codigo).first()
                    
                    if equipo:
                        self.session.delete(equipo)
                        eliminados += 1
                    else:
                        errores.append(f"No se encontró el equipo con código {codigo}")

                self.session.commit()
                
                if errores:
                    QMessageBox.warning(self, "Advertencia", f"Se eliminaron {eliminados} equipos, pero hubo errores:\n" + "\n".join(errores))
                else:
                    QMessageBox.information(self, "Éxito", f"Se eliminaron {eliminados} equipos correctamente.")
                    
                self.load_data()
                
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error al eliminar equipos: {str(e)}")

    def eliminar_rango(self):
        """Elimina un rango de equipos por Código Único (EQxxxxx)."""
        dialog = DeleteRangeDialog(self, title="Eliminar Rango de Equipos", label_text="Ingrese el rango de Códigos Únicos (solo número, ej: 1 para EQ00001):")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            desde, hasta = dialog.get_range()
            
            if not desde.isdigit() or not hasta.isdigit():
                QMessageBox.warning(self, "Error", "Los rangos deben ser numéricos (parte numérica del EQ).")
                return
                
            num_desde = int(desde)
            num_hasta = int(hasta)
            
            if num_desde > num_hasta:
                QMessageBox.warning(self, "Error", "El valor 'Desde' no puede ser mayor que 'Hasta'.")
                return
                
            confirm = QMessageBox.question(self, "Confirmar Eliminación Masiva", 
                                         f"¿Está SEGURO de eliminar los equipos con código único del EQ{num_desde:05d} al EQ{num_hasta:05d}?\n\n"
                                         "Esta acción NO se puede deshacer.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    # Construir lista de códigos a eliminar
                    # Como es string, no podemos usar between directo fácilmente si no formateamos bien
                    # Pero EQxxxxx tiene longitud fija, así que between lexicográfico funciona si generamos los strings
                    
                    cod_desde = f"EQ{num_desde:05d}"
                    cod_hasta = f"EQ{num_hasta:05d}"
                    
                    equipos_a_eliminar = self.session.query(Equipo).filter(
                        Equipo.codigo_unico >= cod_desde,
                        Equipo.codigo_unico <= cod_hasta
                    ).all()
                    
                    if not equipos_a_eliminar:
                        QMessageBox.information(self, "Aviso", "No se encontraron equipos en ese rango.")
                        return
                        
                    count = len(equipos_a_eliminar)
                    confirm2 = QMessageBox.question(self, "Confirmar", f"Se encontraron {count} equipos en el rango.\n¿Proceder a eliminar?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                    if confirm2 == QMessageBox.StandardButton.Yes:
                        eliminados = 0
                        for eq in equipos_a_eliminar:
                            self.session.delete(eq)
                            eliminados += 1
                            
                        self.session.commit()
                        QMessageBox.information(self, "Éxito", f"Se eliminaron {eliminados} equipos.")
                        self.load_data()

                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error al eliminar rango:\n{str(e)}")
