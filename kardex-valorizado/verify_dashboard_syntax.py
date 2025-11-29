import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from views import dashboard_view
    print("SUCCESS: dashboard_view imported successfully.")
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except SyntaxError as e:
    print(f"FAILURE: SyntaxError: {e}")
except Exception as e:
    # It might fail due to missing PyQt6 or other deps in this environment, 
    # but we want to catch syntax errors primarily.
    print(f"WARNING: Import failed with {type(e).__name__}: {e}")
    print("This might be expected if GUI libs are missing, but check for SyntaxErrors.")
