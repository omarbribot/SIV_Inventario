import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-muy-dificil-de-adivinar'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///inventario_v1.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- NUEVA CONFIGURACIÓN PARA IMÁGENES ---
    # Esto define la ruta absoluta a la carpeta 'static/uploads'
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # Opcional: Limita el tamaño a 2MB