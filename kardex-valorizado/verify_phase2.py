import sys
import time
from PyQt6.QtCore import QCoreApplication
from utils.worker import WorkerThread
from schemas.product_schema import ProductCreate
from pydantic import ValidationError

# 1. Test WorkerThread
print("--- Testing WorkerThread ---")
app = QCoreApplication(sys.argv)

def heavy_task(seconds):
    time.sleep(seconds)
    return "Task Completed"

worker = WorkerThread(heavy_task, 1)
worker_finished = False

def on_finished(result):
    global worker_finished
    print(f"Worker finished with result: {result}")
    worker_finished = True
    app.quit()

def on_error(err):
    print(f"Worker error: {err}")
    app.quit()

worker.finished.connect(on_finished)
worker.error.connect(on_error)
worker.start()

print("Worker started, waiting...")
# Run event loop for max 3 seconds
start_time = time.time()
while not worker_finished and time.time() - start_time < 3:
    app.processEvents()
    time.sleep(0.1)

if worker_finished:
    print("WorkerThread Test: PASS")
else:
    print("WorkerThread Test: TIMEOUT/FAIL")

# 2. Test Product Schema
print("\n--- Testing Product Schema ---")

valid_data = {
    "codigo": "ABCDE-123456",
    "nombre": "Producto Test",
    "categoria_id": 1,
    "unidad_medida": "UND",
    "stock_minimo": 10.0,
    "precio_venta": 100.0
}

try:
    p = ProductCreate(**valid_data)
    print("Valid Product: PASS")
except ValidationError as e:
    print(f"Valid Product: FAIL - {e}")

invalid_data = {
    "codigo": "SHORT", # Invalid length
    "nombre": "A", # Too short
    "categoria_id": 0, # Invalid ID
    "unidad_medida": "", # Empty
    "stock_minimo": -1 # Negative
}

try:
    ProductCreate(**invalid_data)
    print("Invalid Product: FAIL (Should have raised error)")
except ValidationError as e:
    print(f"Invalid Product: PASS (Caught expected errors: {len(e.errors())})")
    # for err in e.errors():
    #     print(f" - {err['loc'][0]}: {err['msg']}")
