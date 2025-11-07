"""
Modelo de Base de Datos Completo - Sistema Kardex Valorizado
SQLAlchemy ORM con SQLite
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Date, Enum
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

class RolUsuario(enum.Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    SUPERVISOR = "SUPERVISOR"
    OPERADOR = "OPERADOR"

class EstadoAnio(enum.Enum):
    ABIERTO = "Abierto"
    CERRADO = "Cerrado"

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
    
    # Estado
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    almacenes = relationship("Almacen", back_populates="empresa")
    movimientos = relationship("MovimientoStock", back_populates="empresa")
    ordenes_compra = relationship("OrdenCompra", back_populates="empresa")
    usuarios_asignados = relationship("UsuarioEmpresa", back_populates="empresa")

# ============================================
# TABLA: ALMACENES
# ============================================

class Almacen(Base):
    __tablename__ = 'almacenes'
    
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    
    codigo = Column(String(20), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    ubicacion = Column(String(200))
    
    # Estado
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="almacenes")
    movimientos = relationship("MovimientoStock", back_populates="almacen")

# ============================================
# TABLA: CATEGORIAS
# ============================================

class Categoria(Base):
    __tablename__ = 'categorias'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    productos = relationship("Producto", back_populates="categoria")

# ============================================
# TABLA: PRODUCTOS
# ============================================

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
    
    # Relaciones
    categoria = relationship("Categoria", back_populates="productos")
    fotos = relationship("ProductoFoto", back_populates="producto")
    conversiones = relationship("ConversionUnidad", back_populates="producto")
    movimientos = relationship("MovimientoStock", back_populates="producto")
    detalles_orden = relationship("OrdenCompraDetalle", back_populates="producto")

# ============================================
# TABLA: FOTOS DE PRODUCTOS
# ============================================

class ProductoFoto(Base):
    __tablename__ = 'producto_fotos'
    
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    
    ruta_archivo = Column(String(500), nullable=False)  # Ruta en OneDrive
    es_principal = Column(Boolean, default=False)
    orden = Column(Integer, default=0)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    producto = relationship("Producto", back_populates="fotos")

# ============================================
# TABLA: CONVERSIONES DE UNIDAD
# ============================================

class ConversionUnidad(Base):
    __tablename__ = 'conversiones_unidad'
    
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    
    unidad_origen = Column(String(10), nullable=False)
    unidad_destino = Column(String(10), nullable=False)
    factor_conversion = Column(Float, nullable=False)  # ej: 1 saco = 50 kg
    
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    producto = relationship("Producto", back_populates="conversiones")

# ============================================
# TABLA: PROVEEDORES
# ============================================

class Proveedor(Base):
    __tablename__ = 'proveedores'
    
    id = Column(Integer, primary_key=True)
    
    # Datos obligatorios
    ruc = Column(String(11), unique=True, nullable=False)
    razon_social = Column(String(200), nullable=False)
    
    # Datos opcionales
    direccion = Column(Text)
    telefono = Column(String(20))
    email = Column(String(100))
    contacto = Column(String(100))
    
    # Estado
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    compras = relationship("Compra", back_populates="proveedor")
    ordenes_compra = relationship("OrdenCompra", back_populates="proveedor")

# ============================================
# TABLA: TIPO DE CAMBIO
# ============================================

class TipoCambio(Base):
    __tablename__ = 'tipo_cambio'
    
    id = Column(Integer, primary_key=True)
    fecha = Column(Date, unique=True, nullable=False)
    precio_compra = Column(Float, nullable=False)
    precio_venta = Column(Float, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.now)

# ============================================
# TABLA: ÓRDENES DE COMPRA
# ============================================

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

# ============================================
# TABLA: DETALLE ORDEN DE COMPRA
# ============================================

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
    subtotal = Column(Float, nullable=False)
    
    lote = Column(String(50))
    fecha_vencimiento = Column(Date, nullable=True)
    
    # Relaciones (AÑADIDAS/CORREGIDAS)
    compra = relationship("Compra", back_populates="detalles")
    producto = relationship("Producto")
    almacen = relationship("Almacen")
    
class Destino(Base):
    __tablename__ = 'destinos'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    requisiciones = relationship("Requisicion", back_populates="destino")

# ============================================
# TABLA: REQUISICIONES
# ============================================

class Requisicion(Base):
    __tablename__ = 'requisiciones'
    
    id = Column(Integer, primary_key=True)
    destino_id = Column(Integer, ForeignKey('destinos.id'), nullable=False)
    
    numero_requisicion = Column(String(20), nullable=False)
    fecha = Column(Date, nullable=False)
    solicitante = Column(String(100))
    observaciones = Column(Text)
    
    fecha_registro = Column(DateTime, default=datetime.now)
    
    # Relaciones
    destino = relationship("Destino", back_populates="requisiciones")
    detalles = relationship("RequisicionDetalle", back_populates="requisicion")

# ============================================
# TABLA: DETALLE REQUISICIÓN
# ============================================

class RequisicionDetalle(Base):
    __tablename__ = 'requisicion_detalles'
    
    id = Column(Integer, primary_key=True)
    requisicion_id = Column(Integer, ForeignKey('requisiciones.id'), nullable=False)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
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
    fecha_documento = Column(Date, nullable=False)
    
    # Proveedor o destino según sea ingreso o salida
    proveedor_id = Column(Integer, ForeignKey('proveedores.id'), nullable=True)
    destino_id = Column(Integer, ForeignKey('destinos.id'), nullable=True)
    
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
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="movimientos")
    producto = relationship("Producto", back_populates="movimientos")
    almacen = relationship("Almacen", back_populates="movimientos")

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
    
    rol = Column(Enum(RolUsuario), default=RolUsuario.OPERADOR)
    
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.now)
    ultimo_acceso = Column(DateTime, nullable=True)
    
    # Relaciones
    empresas_asignadas = relationship("UsuarioEmpresa", back_populates="usuario")
    acciones_auditoria = relationship("Auditoria", back_populates="usuario")

# ============================================
# TABLA: USUARIO - EMPRESA (Many-to-Many)
# ============================================

class UsuarioEmpresa(Base):
    __tablename__ = 'usuario_empresas'
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    
    puede_registrar = Column(Boolean, default=True)
    puede_modificar = Column(Boolean, default=False)
    puede_eliminar = Column(Boolean, default=False)
    puede_ver_reportes = Column(Boolean, default=True)
    
    fecha_asignacion = Column(DateTime, default=datetime.now)
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="empresas_asignadas")
    empresa = relationship("Empresa", back_populates="usuarios_asignados")

# ============================================
# TABLA: AUDITORÍA
# ============================================

class Auditoria(Base):
    __tablename__ = 'auditoria'
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    
    accion = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE
    tabla = Column(String(50), nullable=False)
    registro_id = Column(Integer, nullable=False)
    
    datos_anteriores = Column(Text)  # JSON con datos previos
    datos_nuevos = Column(Text)  # JSON con datos nuevos
    
    ip_address = Column(String(45))
    fecha_hora = Column(DateTime, default=datetime.now)
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="acciones_auditoria")

# ============================================
# TABLA: LICENCIA
# ============================================

class Licencia(Base):
    __tablename__ = 'licencia'
    
    id = Column(Integer, primary_key=True)
    codigo_licencia = Column(Text, nullable=False)
    fecha_instalacion = Column(DateTime, default=datetime.now)
    fecha_vencimiento = Column(Date, nullable=False)
    activa = Column(Boolean, default=True)

# ============================================
# FUNCIONES DE INICIALIZACIÓN
# ============================================

def crear_base_datos(db_url='sqlite:///kardex.db'):
    """
    Crea todas las tablas en la base de datos
    """
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(engine)
    print("✓ Base de datos creada exitosamente")
    return engine

def obtener_session(db_url='sqlite:///kardex.db'):
    """
    Obtiene una sesión de SQLAlchemy
    """
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()

def poblar_datos_iniciales(session):
    """
    Crea datos iniciales necesarios
    """
    # Categorías predefinidas
    categorias = [
        Categoria(nombre="MATERIA PRIMA", descripcion="Materiales para producción"),
        Categoria(nombre="SUMINISTRO", descripcion="Suministros diversos"),
        Categoria(nombre="MATERIAL AUXILIAR", descripcion="Materiales auxiliares")
    ]
    
    for cat in categorias:
        session.add(cat)
    
    # Usuario administrador por defecto
    from werkzeug.security import generate_password_hash
    admin = Usuario(
        username="admin",
        password_hash=generate_password_hash("admin123"),
        nombre_completo="Administrador",
        rol=RolUsuario.ADMINISTRADOR
    )
    session.add(admin)
    
    session.commit()
    print("✓ Datos iniciales creados")

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
    print("✓ Base de datos lista para usar")
    print("  Usuario: admin")
    print("  Password: admin123")
    print("=" * 60)