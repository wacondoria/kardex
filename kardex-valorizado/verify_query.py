import sqlite3
import os

DB_PATH = 'kardex.db'

def verify_query():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Attempting to select fecha_salida...")
        cursor.execute("SELECT fecha_salida FROM alquiler_detalles LIMIT 1")
        row = cursor.fetchone()
        print(f"Success! Row: {row}")
        
    except Exception as e:
        print(f"Query failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    verify_query()
