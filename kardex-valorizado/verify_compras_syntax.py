import sys
import os

files = [
    'src/views/compras_window.py',
    'src/views/tipo_cambio_window.py'
]

for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), file_path, 'exec')
        print(f"SUCCESS: {file_path} syntax is valid.")
    except Exception as e:
        print(f"FAILURE: {file_path} SyntaxError: {e}")
