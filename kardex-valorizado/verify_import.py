import sys
import os
sys.path.insert(0, os.path.abspath('src'))
try:
    import main
    print("Successfully imported main")
except Exception as e:
    print(f"Failed to import main: {e}")
    import traceback
    traceback.print_exc()
