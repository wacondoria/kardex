import sqlite3
import os

DB_PATH = 'kardex.db'

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(clientes)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'contacto' in columns:
            print("Column 'contacto' already exists in 'clientes' table.")
        else:
            print("Adding 'contacto' column to 'clientes' table...")
            cursor.execute("ALTER TABLE clientes ADD COLUMN contacto VARCHAR(100)")
            conn.commit()
            print("Column added successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
