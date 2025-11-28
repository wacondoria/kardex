import os

file_path = r"c:\Users\USER\Github\kardex\kardex-valorizado\src\models\database_model.py"

# Read the first 697 lines
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Keep only first 697 lines
lines = lines[:697]

# Missing content
missing_content = """    # Optimistic Locking
    version_id = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {
        "version_id_col": version_id
    }
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="movimientos")
    producto = relationship("Producto", back_populates="movimientos")
    almacen = relationship("Almacen", back_populates="movimientos")

# ============================================
# TABLAS: ROLES Y PERMISOS
# ============================================

# Tabla de Asociación Rol-Permiso
rol_permisos = Table('rol_permisos', Base.metadata,
    Column('rol_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permiso_id', Integer, ForeignKey('permisos.id'), primary_key=True)
)

class Rol(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(255))

    usuarios = relationship('Usuario', back_populates='rol')
    permisos = relationship('Permiso', secondary=rol_permisos, back_populates='roles')

    def __repr__(self):
        return f"<Rol(nombre='{self.nombre}')>"

class Permiso(Base):
    __tablename__ = 'permisos'
    id = Column(Integer, primary_key=True)
    clave = Column(String(50), unique=True, nullable=False) # ej: "ver_modulo_compras"
    descripcion = Column(String(255))

    roles = relationship('Rol', secondary=rol_permisos, back_populates='permisos')

    def __repr__(self):
        return f"<Permiso(clave='{self.clave}')>"

# ============================================
# TABLA: LICENCIAS
# ============================================

class Licencia(Base):
    __tablename__ = 'licencias'
    
    id = Column(Integer, primary_key=True)
    clave = Column(String(255), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    activa = Column(Boolean, default=True)
    tipo = Column(String(50), default="STANDARD")
    
    fecha_registro = Column(DateTime, default=datetime.now)

# ============================================
# TABLA: USUARIOS
# ============================================

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    
    nombre_completo = Column(String(200), nullable=False)
    email = Column(String(100))

    rol_id = Column(Integer, ForeignKey('roles.id'))
    rol = relationship("Rol", back_populates="usuarios")
    
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    ultimo_acceso = Column(DateTime, nullable=True)
    
    # Relaciones
    acciones_auditoria = relationship("Auditoria", back_populates="usuario")
    empresas = relationship("Empresa", secondary="usuario_empresa", back_populates="usuarios")

# ============================================
# TABLA: AUDITORIA
# ============================================

class Auditoria(Base):
    __tablename__ = 'auditoria'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    accion = Column(String(50), nullable=False) # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    tabla = Column(String(50), nullable=True)   # Nombre de la tabla afectada
    registro_id = Column(Integer, nullable=True) # ID del registro afectado
    detalles = Column(Text, nullable=True)      # JSON o texto con los cambios
    fecha = Column(DateTime, default=datetime.now)
    ip_address = Column(String(50), nullable=True)

    usuario = relationship("Usuario", back_populates="acciones_auditoria")

    def __repr__(self):
        return f"<Auditoria(accion='{self.accion}', tabla='{self.tabla}', fecha='{self.fecha}')>"

# ============================================
# TABLA: PROYECTOS
# ============================================

class Proyecto(Base):
    __tablename__ = 'proyectos'

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin_estimada = Column(Date, nullable=True)
    fecha_fin_real = Column(Date, nullable=True)
    
    presupuesto_estimado = Column(Float, default=0.0)
    costo_real = Column(Float, default=0.0)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="proyectos")
    cliente = relationship("Cliente", back_populates="proyectos")
    ventas = relationship("Venta", back_populates="proyecto")
    alquileres = relationship("Alquiler", back_populates="proyecto")
    requisiciones = relationship("Requisicion", back_populates="proyecto")

# ============================================

class Cotizacion(Base):
    __tablename__ = 'cotizaciones'

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    
    numero_cotizacion = Column(String(20), unique=True, nullable=False) # Ej: COT-0001
    fecha_emision = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    
    moneda = Column(Enum(Moneda), default=Moneda.SOLES)
    tipo_cambio = Column(Float, default=1.0)
    
    subtotal = Column(Float, nullable=False)
    igv = Column(Float, default=0)
    total = Column(Float, nullable=False)
    
    estado = Column(Enum(EstadoCotizacion), default=EstadoCotizacion.BORRADOR)
    observaciones = Column(Text)
    
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    cliente = relationship("Cliente")
    detalles = relationship("CotizacionDetalle", back_populates="cotizacion", cascade="all, delete-orphan")

class CotizacionDetalle(Base):
    __tablename__ = 'cotizacion_detalles'

    id = Column(Integer, primary_key=True)
    cotizacion_id = Column(Integer, ForeignKey('cotizaciones.id'), nullable=False)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    
    cantidad = Column(Float, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    # Relaciones
    cotizacion = relationship("Cotizacion", back_populates="detalles")
    producto = relationship("Producto")

# ============================================
# NUEVAS TABLAS: ALQUILER Y OPERACIONES
# ============================================

class Operador(Base):
    __tablename__ = 'operadores'
    
    id = Column(Integer, primary_key=True)
    nombre_completo = Column(String(200), nullable=False)
    dni = Column(String(8), unique=True, nullable=False)
    licencia_conducir = Column(String(20))
    categoria_licencia = Column(String(10))
    fecha_vencimiento_licencia = Column(Date)
    telefono = Column(String(20))
    
    activo = Column(Boolean, default=True)
    
    # Relaciones
    alquileres_detalle = relationship("AlquilerDetalle", back_populates="operador")

class ChecklistModel(Base):
    __tablename__ = 'checklist_modelos'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False) # Ej: "Checklist Camioneta 4x4"
    descripcion = Column(Text)
    tipo_equipo_id = Column(Integer, ForeignKey('tipos_equipo.id'), nullable=True)
    
    activo = Column(Boolean, default=True)
    
    items = relationship("ChecklistItem", back_populates="modelo", cascade="all, delete-orphan")

class ChecklistItem(Base):
    __tablename__ = 'checklist_items'
    
    id = Column(Integer, primary_key=True)
    modelo_id = Column(Integer, ForeignKey('checklist_modelos.id'), nullable=False)
    descripcion = Column(String(200), nullable=False) # Ej: "Nivel de Aceite"
    orden = Column(Integer, default=0)
    es_critico = Column(Boolean, default=False)
    
    modelo = relationship("ChecklistModel", back_populates="items")

class ChecklistInstancia(Base):
    __tablename__ = 'checklist_instancias'
    
    id = Column(Integer, primary_key=True)
    equipo_id = Column(Integer, ForeignKey('equipos.id'), nullable=False)
    alquiler_detalle_id = Column(Integer, ForeignKey('alquiler_detalles.id'), nullable=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    
    fecha = Column(DateTime, default=datetime.now)
    tipo = Column(String(20)) # SALIDA, RETORNO, MANTENIMIENTO
    observaciones = Column(Text)
    aprobado = Column(Boolean, default=True)
    
    detalles = relationship("ChecklistInstanciaDetalle", back_populates="instancia", cascade="all, delete-orphan")

class ChecklistInstanciaDetalle(Base):
    __tablename__ = 'checklist_instancia_detalles'
    
    id = Column(Integer, primary_key=True)
    instancia_id = Column(Integer, ForeignKey('checklist_instancias.id'), nullable=False)
    item_descripcion = Column(String(200)) # Copia del item por si cambia el modelo
    estado = Column(String(20)) # OK, MALO, NO_APLICA
    observacion = Column(String(200))
    
    instancia = relationship("ChecklistInstancia", back_populates="detalles")

class Alquiler(Base):
    __tablename__ = 'alquileres'
    
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    proyecto_id = Column(Integer, ForeignKey('proyectos.id'), nullable=True)
    
    numero_contrato = Column(String(20), unique=True, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin_estimada = Column(Date, nullable=False)
    fecha_fin_real = Column(Date, nullable=True)
    
    moneda = Column(Enum(Moneda), default=Moneda.SOLES)
    tipo_cambio = Column(Float, default=1.0)
    
    subtotal = Column(Float, default=0.0)
    igv = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    
    estado = Column(Enum(EstadoAlquiler), default=EstadoAlquiler.COTIZACION)
    observaciones = Column(Text)
    
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    cliente = relationship("Cliente")
    proyecto = relationship("Proyecto", back_populates="alquileres")
    detalles = relationship("AlquilerDetalle", back_populates="alquiler", cascade="all, delete-orphan")

class AlquilerDetalle(Base):
    __tablename__ = 'alquiler_detalles'
    
    id = Column(Integer, primary_key=True)
    alquiler_id = Column(Integer, ForeignKey('alquileres.id'), nullable=False)
    equipo_id = Column(Integer, ForeignKey('equipos.id'), nullable=False)
    
    fecha_salida = Column(DateTime, nullable=True)
    fecha_retorno = Column(DateTime, nullable=True)
    
    # Horómetros
    horometro_salida = Column(Float, default=0.0)
    horometro_retorno = Column(Float, default=0.0)
    horas_uso = Column(Float, default=0.0)
    
    # Precios
    precio_unitario = Column(Float, nullable=False) # Tarifa diaria
    total = Column(Float, nullable=False)
    
    # Operador
    operador_id = Column(Integer, ForeignKey('operadores.id'), nullable=True)
    
    # Relaciones
    alquiler = relationship("Alquiler", back_populates="detalles")
    equipo = relationship("Equipo", back_populates="detalles_alquiler")
    operador = relationship("Operador", back_populates="alquileres_detalle")
"""

# Append missing content
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
    f.write(missing_content)

print("Successfully updated database_model.py")
