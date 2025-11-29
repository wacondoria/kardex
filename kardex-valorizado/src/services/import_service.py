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

    def generar_plantilla(self, tipo, file_path):
        """Genera un archivo de plantilla para importar"""
        try:
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
