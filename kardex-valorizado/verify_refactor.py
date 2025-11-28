import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.inventory_service import InventoryService
from models.database_model import obtener_session, Empresa

def test_service():
    print("Testing InventoryService...")
    session = obtener_session()
    service = InventoryService(session)
    
    try:
        # Get first company
        empresa = session.query(Empresa).first()
        if not empresa:
            print("No active company found. Skipping query test.")
            return

        print(f"Using Company: {empresa.razon_social}")
        
        # Test get_valorization_report
        print("Running get_valorization_report...")
        report = service.get_valorization_report(empresa_id=empresa.id)
        
        print(f"Report generated successfully. Items found: {len(report)}")
        if len(report) > 0:
            print("First item sample:", report[0])
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        service.close()

if __name__ == "__main__":
    test_service()
