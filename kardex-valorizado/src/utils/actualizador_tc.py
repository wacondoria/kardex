"""
Utilidad de Actualización Automática de Tipo de Cambio
Archivo: src/utils/actualizador_tc.py
"""

import openpyxl
from datetime import datetime, date
from pathlib import Path
import sys

# --- MODIFICADO: Ajustado a tu estructura de proyecto (src/models) ---
# Esto sube un nivel (de src/utils a src/) para encontrar 'models'
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from models.database_model import TipoCambio, obtener_session
except ImportError:
    print("Error: No se pudo importar el modelo de base de datos.")
    sys.exit(1)

def actualizar_tc_desde_excel(session, ruta_excel: str, nombre_hoja: str):
    """
    Actualiza silenciosamente la base de datos con los tipos de cambio
    de un archivo Excel específico.
    
    Usa la lógica "Upsert":
    - Si la fecha no existe, la crea.
    - Si la fecha existe, actualiza los precios y la reactiva.
    """
    
    try:
        wb = openpyxl.load_workbook(ruta_excel, data_only=True)
        ws = wb[nombre_hoja]
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo Excel en: {ruta_excel}")
        return
    except KeyError:
        print(f"Error: No se encontró la hoja '{nombre_hoja}' en el archivo.")
        return
    except Exception as e:
        print(f"Error al abrir el Excel '{ruta_excel}': {e}")
        return

    nuevos = 0
    actualizados = 0
    errores = []

    # Cargar fechas existentes para optimizar
    fechas_en_db = {tc.fecha for tc in session.query(TipoCambio).all()}

    # Empezamos en min_row=2 para saltar el encabezado
    for row_idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        try:
            # --- ESTRUCTURA DE TU EXCEL ---
            # Columna B (índice 1) = Fecha
            # Columna C (índice 2) = Compra
            # Columna D (índice 3) = Venta
            
            # Omitir fila si faltan datos clave
            if not row[1] or not row[2] or not row[3]:
                continue 
            
            # 1. Convertir Fecha (Columna B)
            fecha_excel = row[1]
            if isinstance(fecha_excel, datetime):
                fecha = fecha_excel.date()
            elif isinstance(fecha_excel, date):
                fecha = fecha_excel
            else:
                # Intentar convertir desde string (ajusta el formato si es necesario)
                # Esto asume 'YYYY-MM-DD HH:MM:SS' o similar
                fecha = datetime.strptime(str(fecha_excel).split(' ')[0], '%Y-%m-%d').date()
            
            # 2. Convertir Precios (Columnas C y D)
            precio_compra = float(row[2])
            precio_venta = float(row[3])
            
            # 3. Lógica Upsert
            if fecha in fechas_en_db:
                # Si ya está en la DB, la buscamos para actualizar
                tc_existe = session.query(TipoCambio).filter_by(fecha=fecha).first()
                if tc_existe:
                    # No actualizar si los datos son idénticos (opcional, para eficiencia)
                    if (tc_existe.precio_compra != precio_compra or 
                        tc_existe.precio_venta != precio_venta or 
                        not tc_existe.activo):
                        
                        tc_existe.precio_compra = precio_compra
                        tc_existe.precio_venta = precio_venta
                        tc_existe.activo = True # Reactivarlo si estaba inactivo
                        actualizados += 1
            else:
                # Si no está en la DB, se crea
                tc_nuevo = TipoCambio(
                    fecha=fecha,
                    precio_compra=precio_compra,
                    precio_venta=precio_venta,
                    activo=True
                )
                session.add(tc_nuevo)
                nuevos += 1
                fechas_en_db.add(fecha) # Añadir al set para evitar duplicados en el mismo excel
                
        except Exception as e:
            # Capturar error por fila y continuar
            errores.append(f"Fila {row_idx}: {str(e)}")
            
    try:
        session.commit()
        print("--- Sincronización de TC Automática ---")
        print(f"✓ Éxito: {nuevos} nuevos, {actualizados} actualizados.")
        if errores:
            print(f"⚠️ Errores: {len(errores)} filas omitidas.")
            for err in errores[:5]: # Mostrar solo los primeros 5
                print(f"  - {err}")
    except Exception as e:
        session.rollback()
        print(f"Error Crítico: No se pudo guardar en la BD. Rollback realizado. {e}")