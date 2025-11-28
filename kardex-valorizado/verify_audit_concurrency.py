import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from sqlalchemy import create_engine, inspect
from utils.config import Config

try:
    db_url = Config.get_db_url()
except:
    db_url = 'sqlite:///kardex.db'

engine = create_engine(db_url)
inspector = inspect(engine)

print("--- Verifying Schema Changes ---")

# 1. Check Auditoria table
if 'auditoria' in inspector.get_table_names():
    print("Table 'auditoria': FOUND")
    columns = [c['name'] for c in inspector.get_columns('auditoria')]
    print(f"Columns: {columns}")
else:
    print("Table 'auditoria': MISSING")

# 2. Check version_id in productos
if 'productos' in inspector.get_table_names():
    columns = [c['name'] for c in inspector.get_columns('productos')]
    if 'version_id' in columns:
        print("Column 'productos.version_id': FOUND")
    else:
        print("Column 'productos.version_id': MISSING")
else:
    print("Table 'productos': MISSING")

# 3. Check version_id in movimientos_stock
if 'movimientos_stock' in inspector.get_table_names():
    columns = [c['name'] for c in inspector.get_columns('movimientos_stock')]
    if 'version_id' in columns:
        print("Column 'movimientos_stock.version_id': FOUND")
    else:
        print("Column 'movimientos_stock.version_id': MISSING")
else:
    print("Table 'movimientos_stock': MISSING")
