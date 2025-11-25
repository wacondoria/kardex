import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_model import obtener_session, Equipo

def backfill_codigos():
    session = obtener_session()
    try:
        equipos = session.query(Equipo).filter(Equipo.codigo_unico == None).all()
        print(f"Encontrados {len(equipos)} equipos sin código único.")
        
        # Obtener el último número usado (si hay)
        ultimo = session.query(Equipo).filter(Equipo.codigo_unico.like("EQ%")).order_by(Equipo.codigo_unico.desc()).first()
        start_num = 1
        if ultimo and ultimo.codigo_unico:
            try:
                start_num = int(ultimo.codigo_unico.replace("EQ", "")) + 1
            except:
                pass
        
        print(f"Iniciando desde EQ{start_num:05d}")
        
        for i, eq in enumerate(equipos):
            nuevo_codigo = f"EQ{start_num + i:05d}"
            eq.codigo_unico = nuevo_codigo
            print(f"Asignando {nuevo_codigo} a {eq.codigo}")
            
        session.commit()
        print("Actualización completada.")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    backfill_codigos()
