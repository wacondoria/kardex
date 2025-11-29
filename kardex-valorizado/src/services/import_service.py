import pandas as pd
from models.database_model import obtener_session, Producto, Cliente, Proveedor, Categoria, Almacen, Empresa

class ImportService:
    def __init__(self):
        self.session = obtener_session()

    def importar_productos(self, file_path):
        """Importa productos desde un archivo Excel o CSV"""
        df = self._leer_archivo(file_path)
        if df is None: return False, "No se pudo leer el archivo."

        exito = 0
        errores = []

        # Columnas esperadas: codigo, nombre, categoria, precio_compra, precio_venta, stock_minimo
        requeridos = ['codigo', 'nombre']
        if not all(col in df.columns for col in requeridos):
            return False, f"Faltan columnas requeridas: {requeridos}", []

        for index, row in df.iterrows():
            try:
                codigo = str(row['codigo']).strip()
                if not codigo: continue

                # Verificar existencia
                existe = self.session.query(Producto).filter_by(codigo=codigo).first()
                if existe:
                    errores.append(f"Fila {index+2}: El código {codigo} ya existe.")
                    continue

                # Buscar o crear categoría
                cat_nombre = row.get('categoria', 'General')
                categoria = self.session.query(Categoria).filter_by(nombre=cat_nombre).first()
                if not categoria:
                    categoria = Categoria(nombre=cat_nombre, descripcion="Importada")
                    self.session.add(categoria)
                    self.session.flush()

                prod = Producto(
                    codigo=codigo,
                    nombre=row['nombre'],
                    categoria_id=categoria.id,
                    precio_compra=float(row.get('precio_compra', 0)),
                    precio_venta=float(row.get('precio_venta', 0)),
                    stock_minimo=float(row.get('stock_minimo', 0)),
                    activo=True
                )
                self.session.add(prod)
                exito += 1
            except Exception as e:
                errores.append(f"Fila {index+2}: Error - {str(e)}")

        try:
            self.session.commit()
            return True, f"Importados: {exito}. Errores: {len(errores)}", errores
        except Exception as e:
            self.session.rollback()
            return False, f"Error en commit: {str(e)}", []

    def importar_clientes(self, file_path):
        """Importa clientes desde un archivo Excel o CSV"""
        df = self._leer_archivo(file_path)
        if df is None: return False, "No se pudo leer el archivo.", []

        exito = 0
        errores = []

        # Normalizar columnas del DF (mayúsculas y strip)
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Mapeo de columnas requeridas con posibles alias
        # Clave: Nombre interno, Valor: Lista de posibles nombres en el archivo
        column_aliases = {
            'numero_documento': ['RUC_DNI', 'RUC', 'DNI', 'DOCUMENTO', 'NUMERO DOCUMENTO'],
            'razon_social': ['RAZON_SOCIAL_NOM', 'RAZON SOCIAL', 'NOMBRE', 'N_SOCIAL_NOM', 'RAZON_SOCIAL', 'RAZON_SOCIAL_NOMBRE'],
            'direccion': ['DIRECCION', 'DOMICILIO'],
            'telefono': ['TELEFONO', 'CELULAR', 'MOVIL'],
            'email': ['EMAIL', 'CORREO', 'CORREO ELECTRONICO'],
            'contacto': ['CONTACTO', 'PERSONA_CONTACTO', 'REPRESENTANTE']
        }

        # Identificar columnas presentes
        col_map = {} # Mapping from internal name to actual column name in df
        missing = []

        for internal, aliases in column_aliases.items():
            found = False
            for alias in aliases:
                if alias in df.columns:
                    col_map[internal] = alias
                    found = True
                    break
            
            # Check required columns
            if not found and internal in ['numero_documento', 'razon_social']:
                missing.append(f"{internal} (alias: {', '.join(aliases)})")

        if missing:
            return False, f"Faltan columnas requeridas o no se reconocen:\n{', '.join(missing)}\n\nColumnas encontradas:\n{', '.join(df.columns)}", []

        for index, row in df.iterrows():
            try:
                # Obtener valores usando el mapa de columnas
                doc_col = col_map['numero_documento']
                name_col = col_map['razon_social']
                
                doc = str(row[doc_col]).strip()
                if not doc or doc.lower() == 'nan': continue
                
                # Manejar notación científica o decimales en Excel para documentos numéricos
                if '.' in doc:
                    doc = doc.split('.')[0]

                # Verificar existencia
                existe = self.session.query(Cliente).filter_by(numero_documento=doc).first()
                if existe:
                    errores.append(f"Fila {index+2}: El documento {doc} ya existe.")
                    continue

                # Obtener otros campos opcionales
                dir_val = row.get(col_map.get('direccion')) if 'direccion' in col_map else None
                tel_val = row.get(col_map.get('telefono')) if 'telefono' in col_map else None
                email_val = row.get(col_map.get('email')) if 'email' in col_map else None
                contacto_val = row.get(col_map.get('contacto')) if 'contacto' in col_map else None

                cliente = Cliente(
                    numero_documento=doc,
                    razon_social=str(row[name_col]).strip(),
                    direccion=str(dir_val).strip() if pd.notna(dir_val) else None,
                    telefono=str(tel_val).strip() if pd.notna(tel_val) else None,
                    email=str(email_val).strip() if pd.notna(email_val) else None,
                    contacto=str(contacto_val).strip() if pd.notna(contacto_val) else None,
                    activo=True
                )
                self.session.add(cliente)
                exito += 1
            except Exception as e:
                errores.append(f"Fila {index+2}: Error - {str(e)}")

        try:
            self.session.commit()
            return True, f"Importados: {exito}. Errores: {len(errores)}", errores
        except Exception as e:
            self.session.rollback()
            return False, f"Error en commit: {str(e)}", []

    def importar_proveedores(self, file_path):
        """Importa proveedores desde un archivo Excel o CSV"""
        df = self._leer_archivo(file_path)
        if df is None: return False, "No se pudo leer el archivo.", []

        exito = 0
        errores = []

        # Normalizar columnas del DF
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Mapeo de columnas
        column_aliases = {
            'ruc': ['RUC', 'RUC_DNI', 'NUMERO_DOCUMENTO', 'DOCUMENTO'],
            'razon_social': ['RAZON_SOCIAL', 'RAZON SOCIAL', 'NOMBRE', 'PROVEEDOR', 'EMPRESA'],
            'direccion': ['DIRECCION', 'DOMICILIO'],
            'telefono': ['TELEFONO', 'CELULAR', 'MOVIL'],
            'email': ['EMAIL', 'CORREO', 'CORREO ELECTRONICO'],
            'contacto': ['CONTACTO', 'PERSONA_CONTACTO', 'REPRESENTANTE']
        }

        # Identificar columnas
        col_map = {}
        missing = []

        for internal, aliases in column_aliases.items():
            found = False
            for alias in aliases:
                if alias in df.columns:
                    col_map[internal] = alias
                    found = True
                    break
            
            if not found and internal in ['ruc', 'razon_social']:
                missing.append(f"{internal} (alias: {', '.join(aliases)})")

        if missing:
            return False, f"Faltan columnas requeridas:\n{', '.join(missing)}\n\nColumnas encontradas:\n{', '.join(df.columns)}", []

        for index, row in df.iterrows():
            try:
                ruc_col = col_map['ruc']
                name_col = col_map['razon_social']
                
                ruc = str(row[ruc_col]).strip()
                if not ruc or ruc.lower() == 'nan': continue
                
                if '.' in ruc:
                    ruc = ruc.split('.')[0]

                # Verificar existencia
                existe = self.session.query(Proveedor).filter_by(ruc=ruc).first()
                if existe:
                    errores.append(f"Fila {index+2}: El RUC {ruc} ya existe.")
                    continue

                # Obtener opcionales
                dir_val = row.get(col_map.get('direccion')) if 'direccion' in col_map else None
                tel_val = row.get(col_map.get('telefono')) if 'telefono' in col_map else None
                email_val = row.get(col_map.get('email')) if 'email' in col_map else None
                contacto_val = row.get(col_map.get('contacto')) if 'contacto' in col_map else None

                proveedor = Proveedor(
                    ruc=ruc,
                    razon_social=str(row[name_col]).strip(),
                    direccion=str(dir_val).strip() if pd.notna(dir_val) else None,
                    telefono=str(tel_val).strip() if pd.notna(tel_val) else None,
                    email=str(email_val).strip() if pd.notna(email_val) else None,
                    contacto=str(contacto_val).strip() if pd.notna(contacto_val) else None,
                    activo=True
                )
                self.session.add(proveedor)
                exito += 1
            except Exception as e:
                errores.append(f"Fila {index+2}: Error - {str(e)}")

        try:
            self.session.commit()
            return True, f"Importados: {exito}. Errores: {len(errores)}", errores
        except Exception as e:
            self.session.rollback()
            return False, f"Error en commit: {str(e)}", []

    def importar_tipo_cambio(self, file_path):
        """Importa tipo de cambio desde Excel/CSV"""
        df = self._leer_archivo(file_path)
        if df is None: return False, "No se pudo leer el archivo.", []

        exito = 0
        errores = []
        
        # Columnas: FECHA, COMPRA, VENTA
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        from models.database_model import TipoCambio
        from datetime import datetime

        for index, row in df.iterrows():
            try:
                fecha_val = row.get('FECHA')
                compra_val = row.get('COMPRA')
                venta_val = row.get('VENTA')

                if pd.isna(fecha_val) or pd.isna(compra_val) or pd.isna(venta_val):
                    continue

                # Parsear fecha
                if isinstance(fecha_val, str):
                    fecha_obj = datetime.strptime(fecha_val, '%d/%m/%Y').date()
                else:
                    fecha_obj = fecha_val.date() if hasattr(fecha_val, 'date') else fecha_val

                # Verificar si existe
                existe = self.session.query(TipoCambio).filter_by(fecha=fecha_obj, activo=True).first()
                if existe:
                    # Actualizar
                    existe.compra = float(compra_val)
                    existe.venta = float(venta_val)
                else:
                    tc = TipoCambio(
                        fecha=fecha_obj,
                        compra=float(compra_val),
                        venta=float(venta_val),
                        activo=True
                    )
                    self.session.add(tc)
                exito += 1
            except Exception as e:
                errores.append(f"Fila {index+2}: {str(e)}")

        try:
            self.session.commit()
            return True, f"Importados/Actualizados: {exito}", errores
        except Exception as e:
            self.session.rollback()
            return False, f"Error commit: {e}", []

    def importar_compras(self, file_path):
        """Importa compras (cabecera + detalle en una fila)"""
        df = self._leer_archivo(file_path)
        if df is None: return False, "Error al leer archivo", []
        
        exito = 0
        errores = []
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        from models.database_model import Compra, CompraDetalle, Proveedor, Producto, Almacen, Moneda, TipoDocumento
        from datetime import datetime

        # Agrupar por documento para crear cabecera una vez
        # Clave: (RUC_PROVEEDOR, TIPO_DOC, NUMERO_DOC)
        grupos = df.groupby(['RUC_PROVEEDOR', 'TIPO_DOC', 'NUMERO_DOC'])

        for (ruc, tipo_doc, num_doc), grupo in grupos:
            try:
                # 1. Buscar Proveedor
                prov = self.session.query(Proveedor).filter_by(ruc=str(ruc)).first()
                if not prov:
                    errores.append(f"Proveedor RUC {ruc} no encontrado para doc {num_doc}")
                    continue

                # 2. Datos Cabecera (tomar de la primera fila del grupo)
                first_row = grupo.iloc[0]
                fecha_val = first_row.get('FECHA')
                moneda_str = str(first_row.get('MONEDA', 'SOLES')).upper()
                tc_val = float(first_row.get('TC', 1.0))
                
                if isinstance(fecha_val, str):
                    fecha_obj = datetime.strptime(fecha_val, '%d/%m/%Y').date()
                else:
                    fecha_obj = fecha_val.date() if hasattr(fecha_val, 'date') else fecha_val

                moneda_enum = Moneda.DOLARES if 'DOLAR' in moneda_str or 'USD' in moneda_str else Moneda.SOLES
                tipo_doc_enum = TipoDocumento[tipo_doc] if tipo_doc in TipoDocumento.__members__ else TipoDocumento.FACTURA

                # Crear Compra
                compra = Compra(
                    proveedor_id=prov.id,
                    fecha=fecha_obj,
                    tipo_documento=tipo_doc_enum,
                    numero_documento=str(num_doc),
                    moneda=moneda_enum,
                    tipo_cambio=tc_val,
                    incluye_igv=True, # Asumimos True por defecto
                    subtotal=0, igv=0, total=0 # Se calculará
                )
                self.session.add(compra)
                self.session.flush() # Para tener ID

                total_compra = 0
                subtotal_compra = 0
                igv_compra = 0

                # 3. Detalles
                for idx, row in grupo.iterrows():
                    cod_prod = str(row['CODIGO_PRODUCTO'])
                    cant = float(row['CANTIDAD'])
                    precio = float(row['PRECIO_UNITARIO']) # Asumimos incluye IGV si la cabecera dice True

                    prod = self.session.query(Producto).filter_by(codigo=cod_prod).first()
                    if not prod:
                        errores.append(f"Producto {cod_prod} no encontrado en doc {num_doc}")
                        continue
                    
                    # Asumimos Almacen Principal (ID 1) si no se especifica
                    almacen_id = 1 

                    sub_linea = cant * precio
                    base_linea = sub_linea / 1.18
                    igv_linea = sub_linea - base_linea

                    detalle = CompraDetalle(
                        compra_id=compra.id,
                        producto_id=prod.id,
                        almacen_id=almacen_id,
                        cantidad=cant,
                        precio_unitario_sin_igv=base_linea / cant if cant else 0,
                        subtotal=base_linea
                    )
                    self.session.add(detalle)
                    
                    subtotal_compra += base_linea
                    igv_compra += igv_linea
                    total_compra += sub_linea
                    
                    # Actualizar Stock (Simple)
                    prod.stock_actual = (prod.stock_actual or 0) + cant

                compra.subtotal = subtotal_compra
                compra.igv = igv_compra
                compra.total = total_compra
                
                exito += 1

            except Exception as e:
                errores.append(f"Error procesando doc {num_doc}: {e}")

        try:
            self.session.commit()
            return True, f"Compras procesadas: {exito}", errores
        except Exception as e:
            self.session.rollback()
            return False, f"Error commit: {e}", []

    def importar_ventas(self, file_path):
        """Importa ventas (similar a compras)"""
        # Implementación simplificada similar a compras
        return False, "Importación de ventas aún no implementada en detalle.", []

    def generar_plantilla(self, tipo, file_path):
        """Genera un archivo de plantilla para importar"""
        try:
            df = pd.DataFrame()
            
            if tipo == "Productos":
                cols = ['codigo', 'nombre', 'categoria', 'precio_compra', 'precio_venta', 'stock_minimo']
                df = pd.DataFrame(columns=cols)
                df.loc[0] = ['PROD001', 'Ejemplo Producto', 'General', 100.0, 150.0, 10]
            
            elif tipo == "Clientes":
                cols = ['RUC_DNI', 'RAZON_SOCIAL_NOM', 'DIRECCION', 'TELEFONO', 'EMAIL', 'CONTACTO']
                df = pd.DataFrame(columns=cols)
                df.loc[0] = ['10123456789', 'Juan Perez', 'Av. Principal 123', '999888777', 'juan@example.com', 'Maria Lopez']

            elif tipo == "Proveedores":
                cols = ['RUC', 'RAZON_SOCIAL', 'DIRECCION', 'TELEFONO', 'EMAIL', 'CONTACTO']
                df = pd.DataFrame(columns=cols)
                df.loc[0] = ['20123456789', 'Proveedor Ejemplo SAC', 'Av. Industrial 456', '987654321', 'ventas@proveedor.com', 'Carlos Ruiz']
            
            elif tipo == "Tipo de Cambio":
                cols = ['FECHA', 'COMPRA', 'VENTA']
                df = pd.DataFrame(columns=cols)
                df.loc[0] = ['28/11/2025', 3.750, 3.780]

            elif tipo == "Compras":
                cols = ['FECHA', 'RUC_PROVEEDOR', 'TIPO_DOC', 'NUMERO_DOC', 'MONEDA', 'TC', 'CODIGO_PRODUCTO', 'CANTIDAD', 'PRECIO_UNITARIO']
                df = pd.DataFrame(columns=cols)
                df.loc[0] = ['28/11/2025', '20123456789', 'FACTURA', 'F001-0001', 'SOLES', 1.0, 'PROD001', 10, 100.0]

            else:
                return False, "Tipo de plantilla no soportado."

            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, index=False)
            
            return True, "Plantilla generada exitosamente."
        except Exception as e:
            return False, f"Error al generar plantilla: {e}"

    def _leer_archivo(self, file_path):
        try:
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            elif file_path.endswith(('.xls', '.xlsx')):
                return pd.read_excel(file_path)
            return None
        except:
            return None
