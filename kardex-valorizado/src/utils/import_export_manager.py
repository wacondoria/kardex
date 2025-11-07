"""
Manager Centralizado para Importación y Exportación de Plantillas
Archivo: src/utils/import_export_manager.py
"""
import re
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from models.database_model import obtener_session, Proveedor, Producto, Categoria

# Definición de unidades SUNAT
UNIDADES_SUNAT = [
    "UND - Unidad", "KG - Kilogramo", "GR - Gramo", "LT - Litro",
    "ML - Mililitro", "M - Metro", "M2 - Metro cuadrado", "M3 - Metro cúbico",
    "CJ - Caja", "PQ - Paquete", "BOL - Bolsa", "SAC - Saco",
    "GLN - Galón", "DOC - Docena", "MIL - Millar"
]

class ImportExportManager:
    def __init__(self, parent_widget=None):
        self.parent = parent_widget
        self.session = obtener_session()

    def generar_plantilla(self, modulo):
        """Dispara el método de generación de plantilla según el módulo."""
        if modulo == "Proveedores":
            self._generar_plantilla_proveedores()
        elif modulo == "Productos":
            self._generar_plantilla_productos()
        else:
            QMessageBox.warning(self.parent, "Error", f"El módulo '{modulo}' no es válido para generar plantillas.")

    def importar_datos(self, modulo):
        """Dispara el método de importación de datos según el módulo."""
        if modulo == "Proveedores":
            self._importar_datos_proveedores()
        elif modulo == "Productos":
            self._importar_datos_productos()
        else:
            QMessageBox.warning(self.parent, "Error", f"El módulo '{modulo}' no es válido para importar datos.")

    def _generar_plantilla_proveedores(self):
        """Crea y guarda una plantilla de Excel para la importación de proveedores."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "Guardar Plantilla de Proveedores",
            "plantilla_proveedores.xlsx", "Archivos de Excel (*.xlsx)"
        )

        if not file_path:
            return

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Proveedores"
            headers = ["RUC", "RAZON_SOCIAL", "DIRECCION", "TELEFONO", "EMAIL", "CONTACTO"]
            ws.append(headers)

            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="FF1D6F42", end_color="FF1D6F42", fill_type="solid")
            header_align = Alignment(horizontal="center")

            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align

            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 40
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 20
            ws.column_dimensions['E'].width = 30
            ws.column_dimensions['F'].width = 30

            ws_inst = wb.create_sheet(title="Instrucciones")
            ws_inst.append(["Columna", "Descripción", "Obligatorio"])
            ws_inst.append(["RUC", "RUC de 11 dígitos. Debe empezar con 10, 15, 17 o 20.", "Sí"])
            ws_inst.append(["RAZON_SOCIAL", "Nombre o Razón Social del proveedor.", "Sí"])
            ws_inst.append(["DIRECCION", "Dirección fiscal.", "No"])
            ws_inst.append(["TELEFONO", "Teléfono de contacto.", "No"])
            ws_inst.append(["EMAIL", "Correo electrónico.", "No"])
            ws_inst.append(["CONTACTO", "Nombre de la persona de contacto.", "No"])

            wb.save(file_path)
            QMessageBox.information(self.parent, "Éxito", f"Plantilla guardada en:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"No se pudo guardar la plantilla:\n{str(e)}")

    def _importar_datos_proveedores(self):
        """Importa proveedores desde un archivo Excel."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent, "Importar Proveedores", "", "Archivos de Excel (*.xlsx)"
        )
        if not file_path:
            return

        try:
            wb = load_workbook(file_path, data_only=True)
            if "Proveedores" not in wb.sheetnames:
                QMessageBox.critical(self.parent, "Error de Hoja", "No se encontró la hoja 'Proveedores'.")
                return

            ws = wb["Proveedores"]
            expected_headers = ["RUC", "RAZON_SOCIAL", "DIRECCION", "TELEFONO", "EMAIL", "CONTACTO"]
            actual_headers = [str(cell.value).upper().strip() for cell in ws[1]]
            if actual_headers != expected_headers:
                QMessageBox.critical(self.parent, "Error de Formato", f"Encabezados incorrectos.")
                return

            proveedores_excel, errores_lectura = [], []
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if all(c is None for c in row): break
                ruc, razon_social = (str(row[0]).strip() if row[0] else ""), (str(row[1]).strip() if row[1] else "")
                if not ruc and not razon_social: continue
                if not ruc or not razon_social:
                    errores_lectura.append(f"Fila {row_idx}: RUC y Razón Social son obligatorios.")
                    continue
                if len(ruc) != 11 or not ruc.startswith(('10', '15', '17', '20')):
                    errores_lectura.append(f"Fila {row_idx}: RUC '{ruc}' inválido.")
                    continue
                email = str(row[4]).strip() if row[4] else None
                if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                    errores_lectura.append(f"Fila {row_idx}: Email '{email}' inválido.")
                    continue

                proveedores_excel.append({
                    "ruc": ruc, "razon_social": razon_social,
                    "direccion": str(row[2]).strip() if row[2] else None,
                    "telefono": str(row[3]).strip() if row[3] else None,
                    "email": email, "contacto": str(row[5]).strip() if row[5] else None,
                    "fila": row_idx
                })

            if not proveedores_excel and not errores_lectura:
                QMessageBox.warning(self.parent, "Archivo Vacío", "No se encontraron datos válidos.")
                return

            rucs_excel = {p['ruc'] for p in proveedores_excel}
            existentes_db = self.session.query(Proveedor).filter(Proveedor.ruc.in_(rucs_excel)).all()
            mapa_existentes = {p.ruc: p for p in existentes_db}
            creados, actualizados = 0, 0

            for data in proveedores_excel:
                ruc = data['ruc']
                if ruc in mapa_existentes:
                    prov = mapa_existentes[ruc]
                    prov.razon_social, prov.direccion, prov.telefono, prov.email, prov.contacto, prov.activo = \
                        data['razon_social'], data['direccion'], data['telefono'], data['email'], data['contacto'], True
                    actualizados += 1
                else:
                    prov = Proveedor(**{k: v for k, v in data.items() if k != 'fila'})
                    self.session.add(prov)
                    mapa_existentes[ruc] = prov
                    creados += 1

            self.session.commit()
            self._mostrar_reporte_importacion(creados, actualizados, errores_lectura)

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self.parent, "Error Crítico", f"Ocurrió un error inesperado:\n{str(e)}")
        finally:
            self.session.close()

    def _generar_plantilla_productos(self):
        """Genera una plantilla Excel para la importación masiva de productos."""
        path, _ = QFileDialog.getSaveFileName(
            self.parent, "Guardar Plantilla de Productos",
            "plantilla_productos.xlsx", "Archivos de Excel (*.xlsx)"
        )
        if not path: return

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Productos"

            headers = [
                "CODIGO_PREFIJO", "NOMBRE", "DESCRIPCION", "CATEGORIA", "UNIDAD_MEDIDA",
                "STOCK_MINIMO", "PRECIO_VENTA", "MANEJA_LOTE", "MANEJA_SERIE",
                "TIENE_VENCIMIENTO", "DIAS_VENCIMIENTO"
            ]
            ws.append(headers)

            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="FF1D6F42", end_color="FF1D6F42", fill_type="solid")
            header_align = Alignment(horizontal="center")
            for cell in ws[1]:
                cell.font, cell.fill, cell.alignment = header_font, header_fill, header_align

            dv_sino = DataValidation(type="list", formula1='"SI,NO"', allow_blank=True)
            ws.add_data_validation(dv_sino)
            dv_sino.add('H2:J1000')

            unidades_codigos = [u.split(' - ')[0] for u in UNIDADES_SUNAT]
            dv_unidad = DataValidation(type="list", formula1=f'"{",".join(unidades_codigos)}"', allow_blank=False)
            ws.add_data_validation(dv_unidad)
            dv_unidad.add('E2:E1000')

            categorias = self.session.query(Categoria).filter_by(activo=True).all()
            cat_nombres = [c.nombre.replace('"', "''") for c in categorias]
            if cat_nombres:
                dv_cat = DataValidation(type="list", formula1=f'"{",".join(cat_nombres)}"', allow_blank=False)
                ws.add_data_validation(dv_cat)
                dv_cat.add('D2:D1000')

            ws.column_dimensions['A'].width = 18
            ws.column_dimensions['B'].width = 40
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 25
            ws.column_dimensions['E'].width = 18
            for col in ['F', 'G', 'H', 'I', 'J', 'K']:
                ws.column_dimensions[col].width = 18

            ws_inst = wb.create_sheet(title="Instrucciones")
            ws_inst.append(["Columna", "Descripción", "Obligatorio"])
            ws_inst.append(["CODIGO_PREFIJO", "Prefijo de 5 caracteres para el código (Ej: TUBO0).", "Sí"])
            ws_inst.append(["NOMBRE", "Nombre del producto.", "Sí"])
            ws_inst.append(["DESCRIPCION", "Descripción detallada (opcional).", "No"])
            ws_inst.append(["CATEGORIA", "Nombre exacto de una categoría ya existente.", "Sí"])
            ws_inst.append(["UNIDAD_MEDIDA", "Código de unidad de medida (Ej: UND, KG, M).", "Sí"])
            ws_inst.append(["STOCK_MINIMO", "Valor numérico (opcional, defecto 0).", "No"])
            ws_inst.append(["PRECIO_VENTA", "Valor numérico (opcional, defecto 0).", "No"])
            ws_inst.append(["MANEJA_LOTE", "Escribir 'SI' o 'NO' (opcional, defecto NO).", "No"])
            ws_inst.append(["MANEJA_SERIE", "Escribir 'SI' o 'NO' (opcional, defecto NO).", "No"])
            ws_inst.append(["TIENE_VENCIMIENTO", "Escribir 'SI' o 'NO' (opcional, defecto NO).", "No"])
            ws_inst.append(["DIAS_VENCIMIENTO", "Número de días (solo si la columna anterior es 'SI').", "No"])

            wb.save(path)
            QMessageBox.information(self.parent, "Éxito", f"Plantilla guardada exitosamente en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"No se pudo generar la plantilla:\n{str(e)}")

    def _importar_datos_productos(self):
        """Importa productos desde un archivo Excel."""
        path, _ = QFileDialog.getOpenFileName(
            self.parent, "Abrir Plantilla de Productos", "", "Archivos de Excel (*.xlsx *.xls)"
        )
        if not path: return

        try:
            wb = load_workbook(path, data_only=True)
            if "Productos" not in wb.sheetnames:
                QMessageBox.critical(self.parent, "Error de Hoja", "No se encontró la hoja 'Productos'.")
                return

            ws = wb["Productos"]
            expected_headers = [
                "CODIGO_PREFIJO", "NOMBRE", "DESCRIPCION", "CATEGORIA", "UNIDAD_MEDIDA",
                "STOCK_MINIMO", "PRECIO_VENTA", "MANEJA_LOTE", "MANEJA_SERIE",
                "TIENE_VENCIMIENTO", "DIAS_VENCIMIENTO"
            ]
            actual_headers = [str(cell.value).upper().strip() for cell in ws[1]][:len(expected_headers)]
            if actual_headers != expected_headers:
                QMessageBox.critical(self.parent, "Error de Formato", "Los encabezados no son correctos.")
                return

            productos_a_crear, errores_lectura = [], []
            categorias_db = self.session.query(Categoria).filter_by(activo=True).all()
            cat_map = {cat.nombre.upper(): cat.id for cat in categorias_db}
            unidades_validas = [u.split(' - ')[0] for u in UNIDADES_SUNAT]
            nombres_prefijos_excel = set()

            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if all(c is None for c in row): break
                try:
                    codigo_prefijo = str(row[0]).strip().upper() if row[0] else ""
                    nombre = str(row[1]).strip() if row[1] else ""
                    if not codigo_prefijo and not nombre: continue
                    if len(codigo_prefijo) != 5: raise ValueError(f"Código prefijo debe tener 5 caracteres.")
                    if not nombre: raise ValueError("El Nombre es obligatorio.")

                    categoria_nombre = str(row[3]).strip().upper() if row[3] else ""
                    categoria_id = cat_map.get(categoria_nombre)
                    if not categoria_id: raise ValueError(f"Categoría '{row[3]}' no encontrada.")

                    unidad = str(row[4]).strip().upper() if row[4] else ""
                    if unidad not in unidades_validas: raise ValueError(f"Unidad_Medida '{unidad}' no válida.")

                    stock_min = float(str(row[5]).strip() if row[5] else "0")
                    precio_venta = float(str(row[6]).strip() if row[6] else "0")

                    tiene_lote = (str(row[7]).strip().upper() if row[7] else "NO") == "SI"
                    tiene_serie = (str(row[8]).strip().upper() if row[8] else "NO") == "SI"
                    tiene_vencimiento = (str(row[9]).strip().upper() if row[9] else "NO") == "SI"

                    dias_vencimiento = int(str(row[10]).strip() if row[10] else "0") if tiene_vencimiento else None

                    if (codigo_prefijo, nombre) in nombres_prefijos_excel:
                        raise ValueError(f"Duplicado en Excel: Prefijo '{codigo_prefijo}' y Nombre '{nombre}'.")
                    nombres_prefijos_excel.add((codigo_prefijo, nombre))

                    productos_a_crear.append({
                        "prefijo": codigo_prefijo, "nombre": nombre, "desc": str(row[2]).strip() if row[2] else None,
                        "cat_id": categoria_id, "unidad": unidad, "stock_min": stock_min,
                        "precio": precio_venta, "lote": tiene_lote, "serie": tiene_serie,
                        "dias_venc": dias_vencimiento, "fila": row_idx
                    })
                except Exception as e:
                    errores_lectura.append(f"Fila {row_idx}: {str(e)}")

            if not productos_a_crear and not errores_lectura:
                QMessageBox.warning(self.parent, "Archivo Vacío", "No se encontraron datos válidos.")
                return

            creados = 0
            correlativos_map = {}
            nombres_prefijos_db = {(p.codigo.split('-')[0], p.nombre) for p in self.session.query(Producto).filter_by(activo=True).all()}

            for data in productos_a_crear:
                try:
                    prefijo, nombre = data['prefijo'], data['nombre']
                    if (prefijo, nombre) in nombres_prefijos_db:
                        raise ValueError(f"Ya existe en BD: Prefijo '{prefijo}', Nombre '{nombre}'.")

                    if prefijo not in correlativos_map:
                        ultimo = self.session.query(Producto).filter(Producto.codigo.like(f"{prefijo}-%")).order_by(Producto.codigo.desc()).first()
                        correlativos_map[prefijo] = int(ultimo.codigo.split('-')[1]) if ultimo else 0

                    correlativos_map[prefijo] += 1
                    codigo_completo = f"{prefijo}-{correlativos_map[prefijo]:06d}"

                    producto = Producto(
                        codigo=codigo_completo, nombre=data['nombre'], descripcion=data['desc'],
                        categoria_id=data['cat_id'], unidad_medida=data['unidad'], stock_minimo=data['stock_min'],
                        precio_venta=data['precio'] if data['precio'] > 0 else None, tiene_lote=data['lote'],
                        tiene_serie=data['serie'], dias_vencimiento=data['dias_venc']
                    )
                    self.session.add(producto)
                    creados += 1
                except Exception as e:
                    errores_lectura.append(f"Fila {data['fila']} (Procesando): {str(e)}")

            self.session.commit()
            self._mostrar_reporte_importacion(creados, 0, errores_lectura)

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self.parent, "Error Crítico", f"Ocurrió un error inesperado:\n{str(e)}")
        finally:
            self.session.close()

    def _mostrar_reporte_importacion(self, creados, actualizados, errores):
        """Muestra un resumen de la operación de importación."""
        mensaje = f"Importación completada.\n\n" \
                  f"✅ Nuevos registros creados: {creados}\n" \
                  f"🔄 Registros existentes actualizados: {actualizados}\n"

        if errores:
            mensaje += f"\n⚠️ Se encontraron {len(errores)} errores que fueron omitidos:\n"
            mensaje += "\n".join(errores[:10])
            if len(errores) > 10:
                mensaje += f"\n... y {len(errores) - 10} más."
            QMessageBox.warning(self.parent, "Importación con Errores", mensaje)
        else:
            QMessageBox.information(self.parent, "Importación Exitosa", mensaje)
