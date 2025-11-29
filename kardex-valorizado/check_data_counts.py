import sqlite3
import os

DB_PATH = 'kardex.db'

def check_data():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check Compras
        cursor.execute("SELECT COUNT(*) FROM compras")
        count_compras = cursor.fetchone()[0]
        print(f"Compras count: {count_compras}")
        
        if count_compras > 0:
            cursor.execute("SELECT id, fecha, numero_documento, proveedor_id FROM compras LIMIT 5")
            print("First 5 compras:")
            for row in cursor.fetchall():
                print(row)

        # Check TipoCambio
        cursor.execute("SELECT COUNT(*) FROM tipo_cambio")
        count_tc = cursor.fetchone()[0]
        print(f"TipoCambio count: {count_tc}")
        
        if count_tc > 0:
            cursor.execute("SELECT id, fecha, compra, venta, activo FROM tipo_cambio LIMIT 5")
            print("First 5 tipo_cambio:")
            for row in cursor.fetchall():
                print(row)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_data()
