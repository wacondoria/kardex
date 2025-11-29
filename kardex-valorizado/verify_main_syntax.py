import sys
import os

try:
    with open('main.py', 'r', encoding='utf-8') as f:
        compile(f.read(), 'main.py', 'exec')
    print("SUCCESS: main.py syntax is valid.")
except Exception as e:
    print(f"FAILURE: SyntaxError: {e}")
