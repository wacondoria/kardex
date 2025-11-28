import pytest
from datetime import date
from services.inventory_service import InventoryService
from models.database_model import MovimientoStock, TipoMovimiento

def test_get_stock_actual_empty(session, sample_data):
    """Test stock is 0 for new product"""
    service = InventoryService(session)
    stock = service.get_stock_producto(sample_data["producto"].id, sample_data["almacen"].id)
    assert stock == 0.0

def test_get_valorization_report(session, sample_data):
    """Test valorization report calculation"""
    service = InventoryService(session)
    
    # Create some movements
    # 1. Buy 10 units at 10.0
    mov1 = MovimientoStock(
        empresa_id=sample_data["empresa"].id,
        producto_id=sample_data["producto"].id,
        almacen_id=sample_data["almacen"].id,
        tipo=TipoMovimiento.COMPRA,
        fecha_documento=date(2023, 1, 1),
        cantidad_entrada=10.0,
        cantidad_salida=0.0,
        costo_unitario=10.0,
        costo_total=100.0,
        saldo_cantidad=10.0,
        saldo_costo_total=100.0
    )
    session.add(mov1)
    
    # 2. Buy 5 units at 20.0
    mov2 = MovimientoStock(
        empresa_id=sample_data["empresa"].id,
        producto_id=sample_data["producto"].id,
        almacen_id=sample_data["almacen"].id,
        tipo=TipoMovimiento.COMPRA,
        fecha_documento=date(2023, 1, 2),
        cantidad_entrada=5.0,
        cantidad_salida=0.0,
        costo_unitario=20.0,
        costo_total=100.0,
        saldo_cantidad=15.0,
        saldo_costo_total=200.0
    )
    session.add(mov2)
    session.commit()
    
    # Get report
    report = service.get_valorization_report(sample_data["empresa"].id)
    
    assert len(report) == 1
    item = report[0]
    assert item["codigo"] == sample_data["producto"].codigo
    assert item["cantidad"] == 15.0
    assert item["valor_total"] == 200.0
    assert item["costo_unitario"] == 13.333333333333334 # 200 / 15
