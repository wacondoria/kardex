import sqlite3
import os

DB_PATH = 'kardex.db'

def fix_schema():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(alquiler_detalles)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Existing columns: {columns}")

        columns_to_add = [
            ("fecha_salida", "DATETIME"),
            ("fecha_retorno", "DATETIME"),
            ("horometro_salida", "FLOAT DEFAULT 0"),
            ("horometro_retorno", "FLOAT DEFAULT 0"),
            ("horas_uso", "FLOAT DEFAULT 0"),
            ("operador_id", "INTEGER REFERENCES operadores(id)"),
            ("precio_unitario", "FLOAT DEFAULT 0"), # Check if these exist too, just in case
            ("total", "FLOAT DEFAULT 0")
        ]

        for col_name, col_type in columns_to_add:
            if col_name not in columns:
                print(f"Adding missing column: {col_name}")
                try:
                    cursor.execute(f"ALTER TABLE alquiler_detalles ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError as e:
                    print(f"Error adding {col_name}: {e}")
            else:
                print(f"Column {col_name} already exists.")

        conn.commit()
        print("Schema update completed.")

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_schema()
