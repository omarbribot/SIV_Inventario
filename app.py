from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Usuario, Producto, Categoria, Variante
from config import Config

# IMPORTANTE: Importamos el Blueprint desde la carpeta routes
from routes.inventario import inventario_bp

app = Flask(__name__)
app.config.from_object(Config)

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
        # Esto intenta crear al admin automáticamente si no existe
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(username='admin', rol='admin', nombre_completo='Administrador Sistema')
            admin.password_hash = generate_password_hash('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin automático creado.")
    app.run(debug=True)