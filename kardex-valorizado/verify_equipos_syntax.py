import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from views import equipos_window
    print("SUCCESS: equipos_window imported successfully.")
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except SyntaxError as e:
    print(f"FAILURE: SyntaxError: {e}")
except Exception as e:
    print(f"WARNING: Import failed with {type(e).__name__}: {e}")
    print("This might be expected if GUI libs are missing, but check for SyntaxErrors.")
