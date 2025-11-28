import sys
from pathlib import Path
from decimal import Decimal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.inventory_service import InventoryService
from models.database_model import obtener_session, Empresa, Producto, MovimientoStock, TipoMovimiento
from datetime import datetime

def test_recalculate():
    print("Testing Kardex Recalculation...")
    session = obtener_session()
    service = InventoryService(session)
    
    try:
        # 1. Setup: Get a product and company
        empresa = session.query(Empresa).first()
        producto = session.query(Producto).filter_by(activo=True).first()
        
        if not empresa or not producto:
            print("No data to test.")
            return

        print(f"Testing with Product: {producto.nombre} ({producto.codigo})")
        
        # 2. Corrupt data intentionally (simulate bad balance)
        last_mov = session.query(MovimientoStock).filter_by(
            producto_id=producto.id, 
            empresa_id=empresa.id
        ).order_by(MovimientoStock.id.desc()).first()
        
        if last_mov:
            original_balance = last_mov.saldo_cantidad
            print(f"Original Balance: {original_balance}")
            
            # Corrupt it
            last_mov.saldo_cantidad = -9999
            session.commit()
            print("Corrupted Balance to: -9999")
            
            # 3. Run Recalculate
            print("Running recalculate_kardex...")
            service.recalculate_kardex(producto.id, empresa.id)
            
            # 4. Verify
            session.refresh(last_mov)
            print(f"Restored Balance: {last_mov.saldo_cantidad}")
            
            if last_mov.saldo_cantidad == original_balance:
                print("SUCCESS: Balance restored correctly!")
            else:
                print(f"WARNING: Balance changed. Expected {original_balance}, got {last_mov.saldo_cantidad}. (This might be correct if original was wrong)")
        else:
            print("No movements found for this product.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        service.close()

if __name__ == "__main__":
    test_recalculate()
