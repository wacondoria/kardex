"""
Sistema de Importaciones Masivas y Backup/Restauración
Para Kardex Valorizado
"""

import pandas as pd
import sqlite3
from datetime import datetime
import shutil
import os
from pathlib import Path
import json

# ============================================
# SISTEMA DE IMPORTACIONES MASIVAS
# ============================================

class ImportadorMasivo:
    """
    Maneja todas las importaciones desde Excel
    """
    
    def __init__(self, db_path='kardex.db'):
        self.db_path = db_path
    
    # =====================================
    # 1. TIPO DE CAMBIO
    # =====================================
    
    def generar_plantilla_tipo_cambio(self, ruta_salida='plantilla_tipo_cambio.xlsx'):
        """
        Genera plantilla Excel para importar tipo de cambio
        Columnas: fecha | p_compra | p_venta
        """
        df = pd.DataFrame({
            'fecha': ['2024-01-15', '2024-01-16', '2024-01-17'],
            'p_compra': [3.85, 3.86, 3.84],
            'p_venta': [3.87, 3.88, 3.86]
        })
        
        df.to_excel(ruta_salida, index=False)
        print(f"✓ Plantilla tipo de cambio generada: {ruta_salida}")
        return ruta_salida
    
    def importar_tipo_cambio(self, archivo_excel):
        """
        Importa tipo de cambio desde Excel
        Valida formato y no permite duplicados de fecha
        """
        try:
            # Leer Excel
            df = pd.read_excel(archivo_excel)
            
            # Validar columnas requeridas
            columnas_req = ['fecha', 'p_compra', 'p_venta']
            if not all(col in df.columns for col in columnas_req):
                return False, f"Error: El archivo debe tener columnas: {columnas_req}"
            
            # Convertir fecha
            df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m-%d')
            
            # Conectar a BD
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crear tabla si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tipo_cambio (
                    fecha TEXT PRIMARY KEY,
                    precio_compra REAL,
                    precio_venta REAL,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            registros_nuevos = 0
            registros_actualizados = 0
            
            for _, row in df.iterrows():
                # Verificar si existe
                cursor.execute('SELECT fecha FROM tipo_cambio WHERE fecha = ?', (row['fecha'],))
                existe = cursor.fetchone()
                
                if existe:
                    # Actualizar
                    cursor.execute('''
                        UPDATE tipo_cambio 
                        SET precio_compra = ?, precio_venta = ?
                        WHERE fecha = ?
                    ''', (row['p_compra'], row['p_venta'], row['fecha']))
                    registros_actualizados += 1
                else:
                    # Insertar nuevo
                    cursor.execute('''
                        INSERT INTO tipo_cambio (fecha, precio_compra, precio_venta)
                        VALUES (?, ?, ?)
                    ''', (row['fecha'], row['p_compra'], row['p_venta']))
                    registros_nuevos += 1
            
            conn.commit()
            conn.close()
            
            mensaje = f"✓ Importación exitosa: {registros_nuevos} nuevos, {registros_actualizados} actualizados"
            return True, mensaje
            
        except Exception as e:
            return False, f"Error en importación: {str(e)}"
    
    # =====================================
    # 2. PROVEEDORES
    # =====================================
    
    def generar_plantilla_proveedores(self, ruta_salida='plantilla_proveedores.xlsx'):
        """
        Genera plantilla para importar proveedores
        """
        df = pd.DataFrame({
            'ruc': ['20123456789', '20987654321'],
            'razon_social': ['PROVEEDOR SAC', 'DISTRIBUIDOR EIRL'],
            'direccion': ['Av. Principal 123', 'Jr. Comercio 456'],
            'telefono': ['987654321', '912345678'],
            'email': ['ventas@proveedor.com', 'contacto@distribuidor.com'],
            'contacto': ['Juan Pérez', 'María López']
        })
        
        df.to_excel(ruta_salida, index=False)
        print(f"✓ Plantilla proveedores generada: {ruta_salida}")
        return ruta_salida
    
    def importar_proveedores(self, archivo_excel):
        """
        Importa proveedores masivamente
        Valida RUC duplicado
        """
        try:
            df = pd.read_excel(archivo_excel)
            
            # Validar columnas obligatorias
            if 'ruc' not in df.columns or 'razon_social' not in df.columns:
                return False, "Error: Debe incluir columnas 'ruc' y 'razon_social'"
            
            # Rellenar campos opcionales con vacío
            campos_opcionales = ['direccion', 'telefono', 'email', 'contacto']
            for campo in campos_opcionales:
                if campo not in df.columns:
                    df[campo] = ''
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proveedores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ruc TEXT UNIQUE NOT NULL,
                    razon_social TEXT NOT NULL,
                    direccion TEXT,
                    telefono TEXT,
                    email TEXT,
                    contacto TEXT,
                    activo INTEGER DEFAULT 1,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            nuevos = 0
            actualizados = 0
            errores = []
            
            for idx, row in df.iterrows():
                try:
                    cursor.execute('SELECT id FROM proveedores WHERE ruc = ?', (row['ruc'],))
                    existe = cursor.fetchone()
                    
                    if existe:
                        # Actualizar
                        cursor.execute('''
                            UPDATE proveedores 
                            SET razon_social=?, direccion=?, telefono=?, email=?, contacto=?
                            WHERE ruc=?
                        ''', (row['razon_social'], row.get('direccion', ''), 
                              row.get('telefono', ''), row.get('email', ''), 
                              row.get('contacto', ''), row['ruc']))
                        actualizados += 1
                    else:
                        # Insertar
                        cursor.execute('''
                            INSERT INTO proveedores (ruc, razon_social, direccion, telefono, email, contacto)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (row['ruc'], row['razon_social'], row.get('direccion', ''),
                              row.get('telefono', ''), row.get('email', ''), row.get('contacto', '')))
                        nuevos += 1
                except Exception as e:
                    errores.append(f"Fila {idx+2}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            mensaje = f"✓ Proveedores: {nuevos} nuevos, {actualizados} actualizados"
            if errores:
                mensaje += f"\n⚠️ {len(errores)} errores: {errores[:3]}"
            
            return True, mensaje
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # =====================================
    # 3. PRODUCTOS
    # =====================================
    
    def generar_plantilla_productos(self, ruta_salida='plantilla_productos.xlsx'):
        """
        Genera plantilla para importar productos
        """
        df = pd.DataFrame({
            'codigo': ['ACERO-000001', 'TUBO0-000001'],
            'nombre': ['Plancha de acero 1mm', 'Tubo PVC 2 pulgadas'],
            'descripcion': ['Plancha acero galvanizado', 'Tubo sanitario'],
            'categoria': ['MATERIA PRIMA', 'SUMINISTRO'],
            'unidad_medida': ['KG', 'UND'],
            'stock_minimo': [100, 50],
            'tiene_lote': ['SI', 'NO'],
            'tiene_serie': ['NO', 'NO'],
            'activo': ['SI', 'SI']
        })
        
        df.to_excel(ruta_salida, index=False)
        print(f"✓ Plantilla productos generada: {ruta_salida}")
        return ruta_salida
    
    def importar_productos(self, archivo_excel):
        """
        Importa productos masivamente
        Valida código duplicado
        """
        try:
            df = pd.read_excel(archivo_excel)
            
            # Validar columnas obligatorias
            cols_req = ['codigo', 'nombre', 'categoria', 'unidad_medida']
            if not all(col in df.columns for col in cols_req):
                return False, f"Error: Faltan columnas obligatorias: {cols_req}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    categoria TEXT NOT NULL,
                    unidad_medida TEXT NOT NULL,
                    stock_minimo REAL DEFAULT 0,
                    tiene_lote INTEGER DEFAULT 0,
                    tiene_serie INTEGER DEFAULT 0,
                    activo INTEGER DEFAULT 1,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            nuevos = 0
            actualizados = 0
            
            for _, row in df.iterrows():
                # Convertir SI/NO a 1/0
                tiene_lote = 1 if str(row.get('tiene_lote', 'NO')).upper() == 'SI' else 0
                tiene_serie = 1 if str(row.get('tiene_serie', 'NO')).upper() == 'SI' else 0
                activo = 1 if str(row.get('activo', 'SI')).upper() == 'SI' else 0
                
                cursor.execute('SELECT id FROM productos WHERE codigo = ?', (row['codigo'],))
                existe = cursor.fetchone()
                
                if existe:
                    cursor.execute('''
                        UPDATE productos 
                        SET nombre=?, descripcion=?, categoria=?, unidad_medida=?,
                            stock_minimo=?, tiene_lote=?, tiene_serie=?, activo=?
                        WHERE codigo=?
                    ''', (row['nombre'], row.get('descripcion', ''), row['categoria'],
                          row['unidad_medida'], row.get('stock_minimo', 0),
                          tiene_lote, tiene_serie, activo, row['codigo']))
                    actualizados += 1
                else:
                    cursor.execute('''
                        INSERT INTO productos 
                        (codigo, nombre, descripcion, categoria, unidad_medida, 
                         stock_minimo, tiene_lote, tiene_serie, activo)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (row['codigo'], row['nombre'], row.get('descripcion', ''),
                          row['categoria'], row['unidad_medida'], row.get('stock_minimo', 0),
                          tiene_lote, tiene_serie, activo))
                    nuevos += 1
            
            conn.commit()
            conn.close()
            
            return True, f"✓ Productos: {nuevos} nuevos, {actualizados} actualizados"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # =====================================
    # 4. STOCK INICIAL
    # =====================================
    
    def generar_plantilla_stock_inicial(self, ruta_salida='plantilla_stock_inicial.xlsx'):
        """
        Genera plantilla para importar stock inicial
        """
        df = pd.DataFrame({
            'codigo_producto': ['ACERO-000001', 'TUBO0-000001'],
            'cantidad': [500, 200],
            'costo_unitario': [25.50, 18.00],
            'almacen': ['ALMACEN PRINCIPAL', 'ALMACEN PRINCIPAL'],
            'lote': ['', ''],
            'fecha_ingreso': ['2024-01-01', '2024-01-01']
        })
        
        df.to_excel(ruta_salida, index=False)
        print(f"✓ Plantilla stock inicial generada: {ruta_salida}")
        return ruta_salida
    
    def importar_stock_inicial(self, archivo_excel, empresa_id):
        """
        Importa stock inicial para una empresa
        Se usa al crear empresa nueva
        """
        try:
            df = pd.read_excel(archivo_excel)
            
            cols_req = ['codigo_producto', 'cantidad', 'costo_unitario']
            if not all(col in df.columns for col in cols_req):
                return False, f"Error: Faltan columnas: {cols_req}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabla de movimientos (simplificada para ejemplo)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS movimientos_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id INTEGER,
                    producto_id INTEGER,
                    tipo TEXT,
                    cantidad REAL,
                    costo_unitario REAL,
                    fecha DATE,
                    almacen TEXT,
                    lote TEXT,
                    observaciones TEXT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            registros = 0
            errores = []
            
            for idx, row in df.iterrows():
                try:
                    # Buscar producto por código
                    cursor.execute('SELECT id FROM productos WHERE codigo = ?', 
                                 (row['codigo_producto'],))
                    producto = cursor.fetchone()
                    
                    if not producto:
                        errores.append(f"Fila {idx+2}: Producto {row['codigo_producto']} no existe")
                        continue
                    
                    # Insertar como ingreso inicial
                    cursor.execute('''
                        INSERT INTO movimientos_stock 
                        (empresa_id, producto_id, tipo, cantidad, costo_unitario, 
                         fecha, almacen, lote, observaciones)
                        VALUES (?, ?, 'STOCK_INICIAL', ?, ?, ?, ?, ?, 'Importación stock inicial')
                    ''', (empresa_id, producto[0], row['cantidad'], row['costo_unitario'],
                          row.get('fecha_ingreso', datetime.now().strftime('%Y-%m-%d')),
                          row.get('almacen', 'PRINCIPAL'), row.get('lote', '')))
                    
                    registros += 1
                    
                except Exception as e:
                    errores.append(f"Fila {idx+2}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            mensaje = f"✓ Stock inicial: {registros} productos importados"
            if errores:
                mensaje += f"\n⚠️ {len(errores)} errores"
            
            return True, mensaje
            
        except Exception as e:
            return False, f"Error: {str(e)}"


# ============================================
# SISTEMA DE BACKUP Y RESTAURACIÓN
# ============================================

class BackupManager:
    """
    Gestiona backups automáticos y manuales
    Mantiene últimos 10 backups en OneDrive
    """
    
    def __init__(self, db_path='kardex.db', backup_dir='backups'):
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = 10
    
    def crear_backup(self, tipo='manual', descripcion=''):
        """
        Crea un backup de la base de datos
        
        Args:
            tipo: 'manual' o 'automatico'
            descripcion: descripción opcional del backup
        """
        try:
            # Nombre del archivo con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_backup = f"kardex_backup_{tipo}_{timestamp}.db"
            ruta_backup = self.backup_dir / nombre_backup
            
            # Copiar base de datos
            shutil.copy2(self.db_path, ruta_backup)
            
            # Guardar metadatos
            metadata = {
                'fecha': datetime.now().isoformat(),
                'tipo': tipo,
                'descripcion': descripcion,
                'tamanio_bytes': ruta_backup.stat().st_size,
                'archivo': nombre_backup
            }
            
            metadata_path = ruta_backup.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Limpiar backups antiguos
            self._limpiar_backups_antiguos()
            
            print(f"✓ Backup creado: {nombre_backup}")
            return True, nombre_backup, metadata
            
        except Exception as e:
            print(f"✗ Error al crear backup: {e}")
            return False, None, None
    
    def _limpiar_backups_antiguos(self):
        """
        Mantiene solo los últimos N backups
        Elimina los más antiguos
        """
        backups = sorted(self.backup_dir.glob('kardex_backup_*.db'))
        
        if len(backups) > self.max_backups:
            backups_a_eliminar = backups[:-self.max_backups]
            for backup in backups_a_eliminar:
                backup.unlink()
                # Eliminar también metadatos
                metadata = backup.with_suffix('.json')
                if metadata.exists():
                    metadata.unlink()
                print(f"  Backup antiguo eliminado: {backup.name}")
    
    def listar_backups(self):
        """
        Lista todos los backups disponibles con sus metadatos
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('kardex_backup_*.db'), reverse=True):
            metadata_file = backup_file.with_suffix('.json')
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                # Si no hay metadatos, crear básicos
                metadata = {
                    'fecha': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                    'tipo': 'desconocido',
                    'descripcion': '',
                    'tamanio_bytes': backup_file.stat().st_size,
                    'archivo': backup_file.name
                }
            
            backups.append(metadata)
        
        return backups
    
    def restaurar_backup(self, nombre_backup):
        """
        Restaura la base de datos desde un backup
        CUIDADO: Sobrescribe la base de datos actual
        """
        try:
            ruta_backup = self.backup_dir / nombre_backup
            
            if not ruta_backup.exists():
                return False, f"Backup {nombre_backup} no encontrado"
            
            # Crear backup de seguridad antes de restaurar
            self.crear_backup(tipo='pre_restauracion', 
                            descripcion='Backup automático antes de restaurar')
            
            # Restaurar
            shutil.copy2(ruta_backup, self.db_path)
            
            print(f"✓ Base de datos restaurada desde: {nombre_backup}")
            return True, "Restauración exitosa"
            
        except Exception as e:
            return False, f"Error al restaurar: {str(e)}"
    
    def backup_automatico_diario(self):
        """
        Función para ejecutar en un scheduler diario
        """
        descripcion = f"Backup automático diario - {datetime.now().strftime('%d/%m/%Y')}"
        return self.crear_backup(tipo='automatico', descripcion=descripcion)


# ============================================
# EJEMPLOS DE USO
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("SISTEMA DE IMPORTACIONES Y BACKUP")
    print("=" * 60)
    
    # Crear instancias
    importador = ImportadorMasivo()
    backup_mgr = BackupManager()
    
    print("\n1. GENERANDO PLANTILLAS EXCEL...")
    print("-" * 60)
    importador.generar_plantilla_tipo_cambio()
    importador.generar_plantilla_proveedores()
    importador.generar_plantilla_productos()
    importador.generar_plantilla_stock_inicial()
    
    print("\n2. EJEMPLO: IMPORTAR TIPO DE CAMBIO")
    print("-" * 60)
    # exito, mensaje = importador.importar_tipo_cambio('plantilla_tipo_cambio.xlsx')
    # print(mensaje)
    
    print("\n3. SISTEMA DE BACKUP")
    print("-" * 60)
    
    # Crear backup manual
    print("\nCreando backup manual...")
    exito, nombre, metadata = backup_mgr.crear_backup(
        tipo='manual', 
        descripcion='Backup de prueba'
    )
    if exito:
        print(f"  ✓ Backup creado: {nombre}")
        print(f"  Tamaño: {metadata['tamanio_bytes']/1024:.2f} KB")
    
    # Listar backups
    print("\nBackups disponibles:")
    backups = backup_mgr.listar_backups()
    for i, backup in enumerate(backups, 1):
        fecha = datetime.fromisoformat(backup['fecha']).strftime('%d/%m/%Y %H:%M:%S')
        tamanio = backup['tamanio_bytes'] / 1024
        print(f"  {i}. {backup['archivo']}")
        print(f"     Fecha: {fecha} | Tipo: {backup['tipo']} | Tamaño: {tamanio:.2f} KB")
        if backup['descripcion']:
            print(f"     Descripción: {backup['descripcion']}")
    
    print("\n" + "=" * 60)
    print("✓ Sistema listo para usar")
    print("=" * 60)
