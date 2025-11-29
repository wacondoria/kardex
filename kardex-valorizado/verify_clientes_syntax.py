import sys
import os

try:
    with open('src/views/clientes_window.py', 'r', encoding='utf-8') as f:
        compile(f.read(), 'src/views/clientes_window.py', 'exec')
    print("SUCCESS: clientes_window.py syntax is valid.")
except Exception as e:
    print(f"FAILURE: SyntaxError: {e}")
