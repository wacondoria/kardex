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

    def _leer_archivo(self, file_path):
        try:
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            elif file_path.endswith(('.xls', '.xlsx')):
                return pd.read_excel(file_path)
            return None
        except:
            return None
