from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
db = SQLAlchemy()

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    rol = db.Column(db.String(20), default='vendedor') # admin o vendedor
    nombre_completo = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    productos = db.relationship('Producto', backref='categoria', lazy=True)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(255), default='default.png')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    
    # Relación con las variantes (tallas/colores)
    variantes = db.relationship('Variante', backref='producto', cascade="all, delete-orphan")

class Variante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    sku = db.Column(db.String(50), unique=True) # Código de barras único por talla/color
    talla = db.Column(db.String(20))   # Ejemplo: '42', 'L', 'M'
    color = db.Column(db.String(30))   # Ejemplo: 'Negro', 'Rojo'
    stock = db.Column(db.Integer, default=0)
    precio_compra = db.Column(db.Float, default=0.0)
    precio_venta = db.Column(db.Float, default=0.0)

class Movimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variante_id = db.Column(db.Integer, db.ForeignKey('variante.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) # <--- Nuevo campo
    tipo = db.Column(db.String(10), nullable=False)  # 'ENTRADA' o 'SALIDA'
    cantidad = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(100), nullable=False) 
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones para acceder fácilmente a los datos
    variante = db.relationship('Variante', backref=db.backref('movimientos', lazy=True))
    usuario = db.relationship('Usuario', backref=db.backref('movimientos', lazy=True))