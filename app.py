import os
import sys
import webbrowser
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Usuario, Producto, Categoria, Variante
from config import Config

# IMPORTANTE: Importamos el Blueprint desde la carpeta routes
from routes.inventario import inventario_bp

# --- LÓGICA DE RUTAS ABSOLUTAS ---
if getattr(sys, 'frozen', False):
    # Si es el EXE, usamos la ruta donde se extraen los archivos temporalmente
    base_path = sys._MEIPASS
else:
    # Si es desarrollo normal, usamos la carpeta actual
    base_path = os.path.abspath(".")

app = Flask(__name__, 
            template_folder=os.path.join(base_path, 'templates'), 
            static_folder=os.path.join(base_path, 'static'))

app.config.from_object(Config)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db.init_app(app)

# REGISTRAMOS EL BLUEPRINT
app.register_blueprint(inventario_bp)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

# --- RUTAS DE ACCESO ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_prod = Producto.query.count()
    total_cat = Categoria.query.count()
    stock_bajo = Variante.query.filter(Variante.stock < 5).count()
    
    return render_template('dashboard.html', 
                           total_productos=total_prod, 
                           total_categorias=total_cat,
                           stock_bajo=stock_bajo)

# --- COMANDO CLI ---
@app.cli.command("crear-admin")
def crear_admin():
    if not Usuario.query.filter_by(username='admin').first():
        admin = Usuario(username='admin', rol='admin', nombre_completo='Administrador Sistema')
        admin.password_hash = generate_password_hash('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Usuario admin creado con éxito. Clave: admin123")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(username='admin', rol='admin', nombre_completo='Administrador Sistema')
            admin.password_hash = generate_password_hash('admin123')
            db.session.add(admin)
            db.session.commit()

    # Abrimos el navegador automáticamente
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open("http://127.0.0.1:5000")
    
    # IMPORTANTE: debug=False para el ejecutable
    app.run(host='127.0.0.1', port=5000, debug=False)