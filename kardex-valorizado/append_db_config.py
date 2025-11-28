
file_path = r"c:\Users\USER\Github\kardex\kardex-valorizado\src\models\database_model.py"

content_to_append = """
# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================

# Crear el motor de base de datos
engine = create_engine('sqlite:///kardex.db', echo=False)

# Crear la sesión
Session = sessionmaker(bind=engine)

def obtener_session():
    \"\"\"Retorna una nueva sesión de base de datos\"\"\"
    return Session()

def init_db():
    \"\"\"Inicializa la base de datos creando las tablas\"\"\"
    Base.metadata.create_all(engine)
"""

with open(file_path, 'a', encoding='utf-8') as f:
    f.write(content_to_append)

print("Successfully appended config to database_model.py")
