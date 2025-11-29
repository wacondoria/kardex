import sqlite3
import os

DB_PATH = 'kardex.db'
OUTPUT_FILE = 'schema_dump.txt'

def verify_schema():
    if not os.path.exists(DB_PATH):
        with open(OUTPUT_FILE, 'w') as f:
            f.write(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(OUTPUT_FILE, 'w') as f:
        try:
            cursor.execute("PRAGMA table_info(alquiler_detalles)")
            columns_info = cursor.fetchall()
            f.write(f"Columns in 'alquiler_detalles':\n")
            for col in columns_info:
                f.write(f"{col}\n")
                
        except Exception as e:
            f.write(f"An error occurred: {e}\n")
    
    conn.close()

if __name__ == "__main__":
    verify_schema()
