
import os

file_path = r"c:\Users\USER\Github\kardex\kardex-valorizado\src\models\database_model.py"

models_to_insert = """
# ============================================
# TABLA: DESTINOS
# ============================================

class Destino(Base):
    __tablename__ = 'destinos'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    direccion = Column(Text)
    activo = Column(Boolean, default=True)

# ============================================
# TABLA: TIPO DE CAMBIO
# ============================================

class TipoCambio(Base):
    __tablename__ = 'tipo_cambio'
    
    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False, unique=True)
    compra = Column(Float, nullable=False)
    venta = Column(Float, nullable=False)
    moneda_origen = Column(Enum(Moneda), default=Moneda.DOLARES)
    moneda_destino = Column(Enum(Moneda), default=Moneda.SOLES)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)

"""

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target_str = "# CONFIGURACIÓN DE BASE DE DATOS"

if target_str in content:
    new_content = content.replace(target_str, models_to_insert + "\n" + target_str)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully inserted models before config section.")
else:
    # Fallback: check for engine creation
    target_str_2 = "engine = create_engine"
    if target_str_2 in content:
        new_content = content.replace(target_str_2, models_to_insert + "\n" + target_str_2)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully inserted models before engine creation.")
    else:
        print("Could not find insertion point. Appending to end.")
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(models_to_insert)
