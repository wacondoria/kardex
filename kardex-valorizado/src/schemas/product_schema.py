from pydantic import BaseModel, Field, validator
from typing import Optional

class ProductBase(BaseModel):
    codigo: str = Field(..., min_length=7, max_length=20, description="Código del producto (ej: TUBO0-000001)")
    nombre: str = Field(..., min_length=3, max_length=200, description="Nombre del producto")
    descripcion: Optional[str] = None
    categoria_id: int = Field(..., gt=0, description="ID de la categoría")
    unidad_medida: str = Field(..., min_length=1, max_length=10, description="Unidad de medida (SUNAT)")
    stock_minimo: float = Field(0.0, ge=0, description="Stock mínimo")
    precio_venta: Optional[float] = Field(None, ge=0, description="Precio de venta")
    tiene_lote: bool = False
    tiene_serie: bool = False
    dias_vencimiento: Optional[int] = Field(None, ge=0, description="Días para vencimiento")

    @validator('codigo')
    def validar_formato_codigo(cls, v):
        if '-' not in v:
            raise ValueError('El código debe tener el formato PREFIJO-NUMERO')
        parts = v.split('-')
        if len(parts) != 2:
             raise ValueError('El código debe tener el formato PREFIJO-NUMERO')
        if len(parts[0]) != 5:
            raise ValueError('El prefijo debe tener 5 caracteres')
        return v.upper()

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass
