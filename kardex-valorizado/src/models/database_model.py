"""
Modelo de Base de Datos Completo - Sistema Kardex Valorizado
SQLAlchemy ORM con SQLite
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Date, Enum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()

# ============================================
# ENUMERACIONES
# ============================================

class MetodoValuacion(enum.Enum):
    PEPS = "PEPS"  # FIFO
    UEPS = "UEPS"  # LIFO
    PROMEDIO_PONDERADO = "PROMEDIO_PONDERADO"

class TipoMovimiento(enum.Enum):
    COMPRA = "COMPRA"
    DEVOLUCION_COMPRA = "DEVOLUCION_COMPRA"
    VENTA = "VENTA"
    DEVOLUCION_VENTA = "DEVOLUCION_VENTA"
    REQUISICION = "REQUISICION"
    DEVOLUCION_REQUISICION = "DEVOLUCION_REQUISICION"
    AJUSTE_POSITIVO = "AJUSTE_POSITIVO"
    AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO"
    STOCK_INICIAL = "STOCK_INICIAL"
    TRANSFERENCIA_ENTRADA = "TRANSFERENCIA_ENTRADA"
    TRANSFERENCIA_SALIDA = "TRANSFERENCIA_SALIDA"

class TipoDocumento(enum.Enum):
    FACTURA = "FACTURA"
    BOLETA = "BOLETA"
    GUIA_REMISION = "GUIA_REMISION"
    NOTA_VENTA = "NOTA_VENTA"
    NOTA_CREDITO = "NOTA_CREDITO"
    NOTA_DEBITO = "NOTA_DEBITO"
    ORDEN_COMPRA = "ORDEN_COMPRA"

class Moneda(enum.Enum):
    SOLES = "SOLES"
    DOLARES = "DOLARES"

class EstadoOrden(enum.Enum):
    PENDIENTE = "PENDIENTE"
    PARCIAL = "PARCIAL"
    COMPLETA = "COMPLETA"
    ANULADA = "ANULADA"

class EstadoAnio(enum.Enum):
    ABIERTO = "Abierto"
    CERRADO = "Cerrado"

class TipoAjuste(enum.Enum):
    INGRESO = "INGRESO"
    SALIDA = "SALIDA"

class NivelEquipo(enum.Enum):
    NIVEL_A = "NIVEL_A" # Activo Principal (Máquina Base)
    NIVEL_B = "NIVEL_B" # Cerebro Crítico (Data Logger, etc)
    NIVEL_C = "NIVEL_C" # Juegos de Accesorios
    # Nivel D se maneja como Productos (Consumibles)

class EstadoEquipo(enum.Enum):
    DISPONIBLE = "DISPONIBLE"
    ALQUILADO = "ALQUILADO"
    MANTENIMIENTO = "MANTENIMIENTO"
    CALIBRACION_VENCIDA = "CALIBRACION_VENCIDA"
    BAJA = "BAJA"

class EstadoAlquiler(enum.Enum):
    COTIZACION = "COTIZACION"
    ACTIVO = "ACTIVO"
    FINALIZADO = "FINALIZADO"
    ANULADO = "ANULADO"

class EstadoProyecto(enum.Enum):
    PLANIFICACION = "PLANIFICACION"
    EJECUCION = "EJECUCION"
    PAUSADO = "PAUSADO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"

# ============================================
# TABLA: AÑO CONTABLE
# ============================================

class AnioContable(Base):
    __tablename__ = 'anio_contable'

    id = Column(Integer, primary_key=True)
    anio = Column(Integer, unique=True, nullable=False)
    estado = Column(Enum(EstadoAnio), default=EstadoAnio.ABIERTO, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<AnioContable(anio={self.anio}, estado='{self.estado.value}')>"

# ============================================
# TABLA: EMPRESAS
# ============================================

class Empresa(Base):
    __tablename__ = 'empresas'
    
    id = Column(Integer, primary_key=True)
    ruc = Column(String(11), unique=True, nullable=False)
    razon_social = Column(String(200), nullable=False)
    direccion = Column(Text)
    telefono = Column(String(20))
    email = Column(String(100))
    
    # Configuración
    metodo_valuacion = Column(Enum(MetodoValuacion), default=MetodoValuacion.PROMEDIO_PONDERADO)
    
    # Relaciones
    almacenes = relationship("Almacen", back_populates="empresa")
    movimientos = relationship("MovimientoStock", back_populates="empresa")
    ordenes_compra = relationship("OrdenCompra", back_populates="empresa")
    usuarios = relationship("Usuario", secondary="usuario_empresa", back_populates="empresas")
    proyectos = relationship("Proyecto", back_populates="empresa")

class Almacen(Base):
    __tablename__ = 'almacenes'
    
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    
    codigo = Column(String(20), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    ubicacion = Column(String(200))
    
    es_principal = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="almacenes")
    movimientos = relationship("MovimientoStock", back_populates="almacen")
    
class Categoria(Base):
    __tablename__ = 'categorias'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    productos = relationship("Producto", back_populates="categoria")

class Producto(Base):
    __tablename__ = 'productos'
    
    id = Column(Integer, primary_key=True)
    
    # Código formato: 5chars-6nums (ej: TUBO0-000001)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=False)
    unidad_medida = Column(String(10), nullable=False)  # KG, UND, LT, M, etc (SUNAT)
    
    # Stock
    stock_minimo = Column(Float, default=0)
    
    # Configuración
    tiene_lote = Column(Boolean, default=False)
    tiene_serie = Column(Boolean, default=False)
    dias_vencimiento = Column(Integer, nullable=True)  # Si tiene lote con vencimiento
    
    # Precio (opcional)
    precio_venta = Column(Float, nullable=True)
    
    # Estado
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)

    # Optimistic Locking
    version_id = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {
        "version_id_col": version_id
    }
    
    # Relaciones
    categoria = relationship("Categoria", back_populates="productos")
    fotos = relationship("ProductoFoto", back_populates="producto")
    conversiones = relationship("ConversionUnidad", back_populates="producto")
    movimientos = relationship("MovimientoStock", back_populates="producto")
    detalles_orden = relationship("OrdenCompraDetalle", back_populates="producto")

# ============================================
# TABLA: FOTOS DE PRODUCTOS
# ============================================

class ConversionUnidad(Base):
    __tablename__ = 'conversiones_unidad'
    
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    
    unidad_origen = Column(String(10), nullable=False)
    unidad_destino = Column(String(10), nullable=False)
    factor_conversion = Column(Float, nullable=False)
    
    # Relaciones
    producto = relationship("Producto", back_populates="conversiones")

# ============================================
# TABLA: FOTOS DE PRODUCTOS
# ============================================

class ProductoFoto(Base):
    __tablename__ = 'producto_fotos'
    
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    
    # Relaciones
    producto = relationship("Producto", back_populates="fotos")

class TipoEquipo(Base):
    __tablename__ = 'tipos_equipo'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), unique=True, nullable=False) # Ej: KIT TERMOFUSIÓN 315
    descripcion = Column(Text)
    activo = Column(Boolean, default=True)
    
    equipos = relationship("Equipo", back_populates="tipo_equipo")
    componentes = relationship("KitComponente", back_populates="tipo_equipo", cascade="all, delete-orphan")
    subtipos = relationship("SubtipoEquipo", back_populates="tipo_equipo", cascade="all, delete-orphan")

class SubtipoEquipo(Base):
    __tablename__ = 'subtipos_equipo'

    id = Column(Integer, primary_key=True)
    tipo_equipo_id = Column(Integer, ForeignKey('tipos_equipo.id'), nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    activo = Column(Boolean, default=True)

    tipo_equipo = relationship("TipoEquipo", back_populates="subtipos")
    equipos = relationship("Equipo", back_populates="subtipo_equipo")

class Equipo(Base):
    __tablename__ = 'equipos'

    id = Column(Integer, primary_key=True)
    
    # Identificación
    codigo = Column(String(50), unique=True, nullable=False) # Ej: MQ-315-A
    codigo_unico = Column(String(20), unique=True, nullable=True) # Ej: EQ00001 (Nuevo correlativo global)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    nivel = Column(Enum(NivelEquipo), nullable=False)
    
    # Clasificación
    tipo_equipo_id = Column(Integer, ForeignKey('tipos_equipo.id'), nullable=True)
    subtipo_equipo_id = Column(Integer, ForeignKey('subtipos_equipo.id'), nullable=True)
    capacidad = Column(String(100)) # Ej: 5000W, 300KG
    
    # Estado y Ubicación
    estado = Column(Enum(EstadoEquipo), default=EstadoEquipo.DISPONIBLE)
    almacen_id = Column(Integer, ForeignKey('almacenes.id'), nullable=True) # Ubicación actual
    
    # Proveedor / Propietario (Datos Alquiler)
    proveedor_id = Column(Integer, ForeignKey('proveedores.id'), nullable=True)

    # Control Técnico
    marca = Column(String(100))
    modelo = Column(String(100))
    serie_modelo = Column(String(100)) # Nueva columna
    serie = Column(String(100))
    anio_fabricacion = Column(Integer)
    
    # Mantenimiento y Calibración
    requiere_calibracion = Column(Boolean, default=False)
    fecha_ultima_calibracion = Column(Date)
    fecha_vencimiento_calibracion = Column(Date)
    
    control_horometro = Column(Boolean, default=False)
    horometro_actual = Column(Float, default=0.0)
    horas_mantenimiento = Column(Float, default=250.0) # Cada cuánto toca mant.
    ultimo_mantenimiento_horometro = Column(Float, default=0.0)
    
    # Financiero
    valor_adquisicion = Column(Float, default=0.0)
    fecha_adquisicion = Column(Date)
    tarifa_diaria_referencial = Column(Float, default=0.0) # Soles
    tarifa_diaria_dolares = Column(Float, default=0.0) # Dólares
    
    # Multimedia
    foto_referencia = Column(String(500))
    
    fecha_registro = Column(DateTime, default=datetime.now)
    activo = Column(Boolean, default=True)

    # Relaciones
    almacen = relationship("Almacen")
    tipo_equipo = relationship("TipoEquipo", back_populates="equipos")
    subtipo_equipo = relationship("SubtipoEquipo", back_populates="equipos")
    proveedor = relationship("Proveedor")
    componentes_kit = relationship("KitComponente", back_populates="equipo_default")
    detalles_alquiler = relationship("AlquilerDetalle", back_populates="equipo")

class KitComponente(Base):
    __tablename__ = 'kit_componentes'

    id = Column(Integer, primary_key=True)
    tipo_equipo_id = Column(Integer, ForeignKey('tipos_equipo.id'), nullable=False)
    
    nombre_componente = Column(String(100), nullable=False) # Ej: "Generador Eléctrico"
    nivel_requerido = Column(Enum(NivelEquipo), nullable=True)
    
    # Equipo por defecto (sugerido)
    equipo_default_id = Column(Integer, ForeignKey('equipos.id'), nullable=True)
    
    cantidad = Column(Integer, default=1)
    es_opcional = Column(Boolean, default=False)
    
    tipo_equipo = relationship("TipoEquipo", back_populates="componentes")
    equipo_default = relationship("Equipo", back_populates="componentes_kit")

class Proveedor(Base):
    __tablename__ = 'proveedores'
    
    id = Column(Integer, primary_key=True)
    ruc = Column(String(11), unique=True, nullable=False)
    razon_social = Column(String(200), nullable=False)
    direccion = Column(Text)
    telefono = Column(String(20))
    email = Column(String(100))
    contacto = Column(String(100))
    
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    ordenes_compra = relationship("OrdenCompra", back_populates="proveedor")
    compras = relationship("Compra", back_populates="proveedor")

class Cliente(Base):
    __tablename__ = 'clientes'
    
    id = Column(Integer, primary_key=True)
    tipo_documento = Column(String(20), default="RUC") # RUC, DNI
    numero_documento = Column(String(20), unique=True, nullable=False)
    razon_social = Column(String(200), nullable=False)
    direccion = Column(Text)
    telefono = Column(String(20))
    email = Column(String(100))
    
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    proyectos = relationship("Proyecto", back_populates="cliente")
    ventas = relationship("Venta", back_populates="cliente")

class OrdenCompra(Base):
    __tablename__ = 'ordenes_compra'
    
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    proveedor_id = Column(Integer, ForeignKey('proveedores.id'), nullable=False)
    
    numero_orden = Column(String(20), nullable=False)
    fecha = Column(Date, nullable=False)
    
    moneda = Column(Enum(Moneda), default=Moneda.SOLES)
    tipo_cambio = Column(Float, default=1.0)
    
    observaciones = Column(Text)
    estado = Column(Enum(EstadoOrden), default=EstadoOrden.PENDIENTE)
    
    # Aprobación
    requiere_aprobacion = Column(Boolean, default=False)
    aprobado = Column(Boolean, default=False)
    aprobado_por = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    fecha_aprobacion = Column(DateTime, nullable=True)
    
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="ordenes_compra")
    proveedor = relationship("Proveedor", back_populates="ordenes_compra")
    detalles = relationship("OrdenCompraDetalle", back_populates="orden")
    compras_generadas = relationship("Compra", back_populates="orden_compra")

class OrdenCompraDetalle(Base):
    __tablename__ = 'orden_compra_detalles'
    
    id = Column(Integer, primary_key=True)
    orden_id = Column(Integer, ForeignKey('ordenes_compra.id'), nullable=False)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    
    cantidad = Column(Float, nullable=False)
    cantidad_recibida = Column(Float, default=0)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    # Relaciones
    orden = relationship("OrdenCompra", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_orden")

# ============================================
# TABLA: COMPRAS
# ============================================

class Compra(Base):
    __tablename__ = 'compras'
    
    id = Column(Integer, primary_key=True)
    proveedor_id = Column(Integer, ForeignKey('proveedores.id'), nullable=False)
    orden_compra_id = Column(Integer, ForeignKey('ordenes_compra.id'), nullable=True)
    
    # Documento
    numero_proceso = Column(String(20), nullable=True)
    tipo_documento = Column(Enum(TipoDocumento), default=TipoDocumento.FACTURA)
    numero_documento = Column(String(20), nullable=False)
    fecha = Column(Date, nullable=False) # Fecha de Emisión (Kardex)
    fecha_registro_contable = Column(Date, nullable=True) # Fecha Periodo Contable
    
    # Moneda y cambio
    moneda = Column(Enum(Moneda), default=Moneda.SOLES)
    tipo_cambio = Column(Float, default=1.0)
    
    # IGV
    incluye_igv = Column(Boolean, default=False)
    igv_porcentaje = Column(Float, default=18.0)
    
    # Totales
    subtotal = Column(Float, nullable=False)
    igv = Column(Float, default=0)
    total = Column(Float, nullable=False)
    
    # Costos adicionales
    costo_adicional = Column(Float, default=0)
    descripcion_costo = Column(Text)
    
    ruta_archivo = Column(String(500))
    observaciones = Column(Text)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    proveedor = relationship("Proveedor", back_populates="compras")
    orden_compra = relationship("OrdenCompra", back_populates="compras_generadas")
    detalles = relationship("CompraDetalle", back_populates="compra", cascade="all, delete-orphan") # Añadido cascade

# ============================================
# TABLA: DETALLE DE COMPRA
# ============================================

class CompraDetalle(Base):
    __tablename__ = 'compra_detalles'
    
    id = Column(Integer, primary_key=True)
    compra_id = Column(Integer, ForeignKey('compras.id'), nullable=False)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    almacen_id = Column(Integer, ForeignKey('almacenes.id'), nullable=False)
    
    cantidad = Column(Float, nullable=False)
    precio_unitario_sin_igv = Column(Float, nullable=False)

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)
    tipo = Column(Enum(TipoAjuste), nullable=False) # Si es para INGRESO o SALIDA
    activo = Column(Boolean, default=True)

    # Relaciones
    ajustes = relationship("AjusteInventario", back_populates="motivo")

# ============================================
# TABLA: AJUSTES DE INVENTARIO
# ============================================

class AjusteInventario(Base):
    __tablename__ = 'ajustes_inventario'

    id = Column(Integer, primary_key=True)
    motivo_id = Column(Integer, ForeignKey('motivos_ajuste.id'), nullable=False)

    numero_ajuste = Column(String(20), nullable=False, unique=True)
    tipo = Column(Enum(TipoAjuste), nullable=False)
    fecha = Column(Date, nullable=False)
    observaciones = Column(Text)

    fecha_registro = Column(DateTime, default=datetime.now)

    # Relaciones
    motivo = relationship("MotivoAjuste", back_populates="ajustes")
    detalles = relationship("AjusteInventarioDetalle", back_populates="ajuste")

# ============================================
# TABLA: DETALLE AJUSTE DE INVENTARIO
# ============================================

class AjusteInventarioDetalle(Base):
    __tablename__ = 'ajuste_inventario_detalles'

    id = Column(Integer, primary_key=True)
    ajuste_id = Column(Integer, ForeignKey('ajustes_inventario.id'), nullable=False)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    almacen_id = Column(Integer, ForeignKey('almacenes.id'), nullable=False)

    cantidad = Column(Float, nullable=False)
    costo_unitario = Column(Float, nullable=True) # Editable para ingresos

    # Relaciones
    ajuste = relationship("AjusteInventario", back_populates="detalles")
    producto = relationship("Producto")
    almacen = relationship("Almacen")
    almacen_id = Column(Integer, ForeignKey('almacenes.id'), nullable=False)
    
    cantidad = Column(Float, nullable=False)
    lote = Column(String(50))  # Si el producto tiene lote
    
    # Relaciones
    requisicion = relationship("Requisicion", back_populates="detalles")
    producto = relationship("Producto")
    almacen = relationship("Almacen")

# ============================================
# TABLA: MOVIMIENTOS DE STOCK (KARDEX)
# ============================================

class MovimientoStock(Base):
    __tablename__ = 'movimientos_stock'
    
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    almacen_id = Column(Integer, ForeignKey('almacenes.id'), nullable=False)
    
    # Tipo de movimiento
    tipo = Column(Enum(TipoMovimiento), nullable=False)
    
    # Documento relacionado
    tipo_documento = Column(Enum(TipoDocumento), nullable=True)
    numero_documento = Column(String(20))
    fecha_documento = Column(Date, nullable=False, index=True)
    
    # Proveedor o destino según sea ingreso o salida
    proveedor_id = Column(Integer, ForeignKey('proveedores.id'), nullable=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=True)
    destino_id = Column(Integer, ForeignKey('destinos.id'), nullable=True)
    motivo_ajuste_id = Column(Integer, ForeignKey('motivos_ajuste.id'), nullable=True)
    
    # Movimiento
    cantidad_entrada = Column(Float, default=0)
    cantidad_salida = Column(Float, default=0)
    
    # Costos (sin IGV siempre)
    costo_unitario = Column(Float, nullable=False)
    costo_total = Column(Float, nullable=False)
    
    # Saldo después del movimiento
    saldo_cantidad = Column(Float, nullable=False)
    saldo_costo_total = Column(Float, nullable=False)
    
    # Lote/Serie
    lote = Column(String(50))
    serie = Column(String(50))
    fecha_vencimiento = Column(Date, nullable=True)
    
    # Moneda original
    moneda = Column(Enum(Moneda), default=Moneda.SOLES)
    tipo_cambio = Column(Float, default=1.0)
    
    observaciones = Column(Text)
    fecha_registro = Column(DateTime, default=datetime.now)

    # Optimistic Locking
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
# TABLA DE ASOCIACIÓN: USUARIO - EMPRESA
# ============================================

usuario_empresa = Table('usuario_empresa', Base.metadata,
    Column('usuario_id', Integer, ForeignKey('usuarios.id'), primary_key=True),
    Column('empresa_id', Integer, ForeignKey('empresas.id'), primary_key=True)
)

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

    usuario = relationship("Usuario")

    def __repr__(self):
        return f"<Auditoria(accion='{self.accion}', tabla='{self.tabla}', fecha='{self.fecha}')>"

# ============================================
# TABLA: LICENCIA
# ============================================

class Licencia(Base):
    __tablename__ = 'licencia'
    
    id = Column(Integer, primary_key=True)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="proyectos")
    cliente = relationship("Cliente", back_populates="proyectos")
    ventas = relationship("Venta", back_populates="proyecto")
    alquileres = relationship("Alquiler", back_populates="proyecto")
    requisiciones = relationship("Requisicion", back_populates="proyecto")

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
    
    estado = Column(Enum(EstadoProyecto), default=EstadoProyecto.PLANIFICACION)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="proyectos")
    cliente = relationship("Cliente", back_populates="proyectos")
    ventas = relationship("Venta", back_populates="proyecto")
    alquileres = relationship("Alquiler", back_populates="proyecto")
    requisiciones = relationship("Requisicion", back_populates="proyecto")

def poblar_datos_iniciales(session):
    """
    Crea datos iniciales necesarios
    """
    # Categorías predefinidas
    categorias_data = [
        {"nombre": "MATERIA PRIMA", "descripcion": "Materiales para producción"},
        {"nombre": "SUMINISTRO", "descripcion": "Suministros diversos"},
        {"nombre": "MATERIAL AUXILIAR", "descripcion": "Materiales auxiliares"}
    ]
    
    for cat_data in categorias_data:
        existe = session.query(Categoria).filter_by(nombre=cat_data["nombre"]).first()
        if not existe:
            cat = Categoria(**cat_data)
            session.add(cat)
    
    # Usuario administrador por defecto
    from werkzeug.security import generate_password_hash

    # Crear Permisos
    permisos_data = {
        'acceso_total': {'clave': 'acceso_total', 'descripcion': 'Acceso sin restricciones a todas las funcionalidades.'},
        'ver_dashboard': {'clave': 'ver_dashboard', 'descripcion': 'Ver el panel principal.'},
        'gestionar_compras': {'clave': 'gestionar_compras', 'descripcion': 'Crear, ver y editar compras.'},
        'gestionar_ventas': {'clave': 'gestionar_ventas', 'descripcion': 'Crear, ver y editar ventas.'},
        'gestionar_requisiciones': {'clave': 'gestionar_requisiciones', 'descripcion': 'Crear, ver y editar requisiciones.'},
        'gestionar_inventario': {'clave': 'gestionar_inventario', 'descripcion': 'Gestionar productos, categorías y ajustes.'},
        'ver_reportes': {'clave': 'ver_reportes', 'descripcion': 'Acceder y generar reportes.'},
        'gestionar_usuarios': {'clave': 'gestionar_usuarios', 'descripcion': 'Crear, editar y eliminar usuarios y roles.'},
        'configuracion_sistema': {'clave': 'configuracion_sistema', 'descripcion': 'Acceder a la configuración del sistema.'}
    }
    
    permisos_objs = {}
    for key, p_data in permisos_data.items():
        permiso = session.query(Permiso).filter_by(clave=p_data['clave']).first()
        if not permiso:
            permiso = Permiso(**p_data)
            session.add(permiso)
            session.flush() # Para tener ID
        permisos_objs[key] = permiso

    # Crear Roles y Asignar Permisos
    roles_data = [
        {
            'nombre': 'Administrador', 
            'descripcion': 'Acceso total al sistema.',
            'permisos': list(permisos_objs.values())
        },
        {
            'nombre': 'Supervisor', 
            'descripcion': 'Acceso a módulos de gestión y reportes.',
            'permisos': [
                permisos_objs['ver_dashboard'],
                permisos_objs['gestionar_compras'],
                permisos_objs['gestionar_ventas'],
                permisos_objs['gestionar_requisiciones'],
                permisos_objs['ver_reportes']
            ]
        },
        {
            'nombre': 'Operador', 
            'descripcion': 'Acceso limitado a operaciones diarias.',
            'permisos': [
                permisos_objs['ver_dashboard'],
                permisos_objs['gestionar_compras'],
                permisos_objs['gestionar_ventas'],
                permisos_objs['gestionar_requisiciones']
            ]
        }
    ]

    rol_admin_obj = None
    for r_data in roles_data:
        rol = session.query(Rol).filter_by(nombre=r_data['nombre']).first()
        if not rol:
            rol = Rol(nombre=r_data['nombre'], descripcion=r_data['descripcion'])
            session.add(rol)
            session.flush()
            rol.permisos = r_data['permisos']
        
        if r_data['nombre'] == 'Administrador':
            rol_admin_obj = rol

    session.commit() # Commit roles and permissions first

    # Crear Usuario Administrador y Asignar Rol
    admin_user = session.query(Usuario).filter_by(username="admin").first()
    if not admin_user and rol_admin_obj:
        admin = Usuario(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            nombre_completo="Administrador del Sistema",
            rol_id=rol_admin_obj.id
        )
        
        # Asignar empresa al admin si existe alguna
        primera_empresa = session.query(Empresa).first()
        if primera_empresa:
            admin.empresas.append(primera_empresa)
            
    pass

def crear_base_datos(db_url=None):
    """
    Crea todas las tablas en la base de datos
    """
    if db_url is None:
        try:
            from utils.config import Config
            db_url = Config.get_db_url()
        except ImportError:
            db_url = 'sqlite:///kardex.db'
        
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(engine)
    print(f"[OK] Base de datos creada exitosamente en: {db_url}")
    return engine

def obtener_session(db_url=None):
    """
    Obtiene una sesión de SQLAlchemy
    """
    if db_url is None:
        try:
            from utils.config import Config
            db_url = Config.get_db_url()
        except ImportError:
            db_url = 'sqlite:///kardex.db'
        
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()

# ============================================
# SCRIPT PRINCIPAL
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("INICIALIZANDO BASE DE DATOS - KARDEX VALORIZADO")
    print("=" * 60)
    
    # Crear base de datos
    engine = crear_base_datos()
    
    # Poblar datos iniciales
    session = obtener_session()
    poblar_datos_iniciales(session)
    session.close()
    
    print("\n" + "=" * 60)
    print("[OK] Base de datos lista para usar")
    print("  Usuario: admin")
    print("  Password: admin123")
    print("=" * 60)