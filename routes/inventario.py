import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Categoria, Producto, Variante, Movimiento

# Definimos el Blueprint
inventario_bp = Blueprint('inventario', __name__)

@inventario_bp.route('/categorias', methods=['GET', 'POST'])
@login_required
def categorias():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if nombre:
            nueva_cat = Categoria(nombre=nombre)
            db.session.add(nueva_cat)
            db.session.commit()
            flash('Categoría creada', 'success')
    
    todas = Categoria.query.all()
    return render_template('categorias.html', categorias=todas)

@inventario_bp.route('/productos')
@login_required
def ver_inventario():
    categoria_id = request.args.get('categoria_id')
    
    # Consulta base
    query = Producto.query
    
    # Filtro por categoría si se selecciona una
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    
    productos = query.all()
    categorias = Categoria.query.all()
    
    return render_template('inventario.html', productos=productos, categorias=categorias)

@inventario_bp.route('/producto/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_producto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        categoria_id = request.form.get('categoria_id')
        descripcion = request.form.get('descripcion')

        # --- Lógica de Imagen ---
        file = request.files.get('imagen')
        filename = 'default.png' 

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        # 1. Crear el producto base
        nuevo_p = Producto(
            nombre=nombre, 
            categoria_id=categoria_id, 
            descripcion=descripcion,
            imagen=filename
        )
        db.session.add(nuevo_p)
        db.session.flush() 

        # 2. Capturar las listas de variantes
        tallas = request.form.getlist('talla[]')
        colores = request.form.getlist('color[]')
        stocks = request.form.getlist('stock[]')
        precios = request.form.getlist('precio[]')

        # 3. Guardar cada variante y registrar movimiento inicial
        for i in range(len(colores)): 
            if colores[i] or precios[i]:
                stock_inicial = int(stocks[i] or 0)
                v = Variante(
                    producto_id=nuevo_p.id,
                    talla=tallas[i] if tallas[i] else "N/A", 
                    color=colores[i],
                    stock=stock_inicial,
                    precio_venta=float(precios[i] or 0)
                )
                db.session.add(v)
                db.session.flush() 

                if stock_inicial > 0:
                    mov_inicial = Movimiento(
                        variante_id=v.id,
                        usuario_id=current_user.id,
                        tipo='ENTRADA',
                        cantidad=stock_inicial,
                        motivo='Carga Inicial de Inventario'
                    )
                    db.session.add(mov_inicial)

        db.session.commit()

        # --- Lógica de redirección según el botón presionado ---
        accion = request.form.get('accion')
        if accion == 'finalizar':
            flash(f'Producto {nombre} guardado. ¡Carga finalizada!', 'success')
            return redirect(url_for('inventario.ver_inventario'))
        else:
            flash(f'¡{nombre} registrado! Formulario listo para el siguiente.', 'success')
            return redirect(url_for('inventario.nuevo_producto'))

    categorias = Categoria.query.all()
    return render_template('nuevo_producto.html', categorias=categorias)

@inventario_bp.route('/historial')
@login_required
def ver_historial():
    # Obtenemos los filtros desde la URL
    fecha_filtro = request.args.get('fecha')
    producto_filtro = request.args.get('producto')

    # Consulta base
    query = Movimiento.query

    # Filtro por producto (buscamos en el nombre del producto o variante)
    if producto_filtro:
        query = query.join(Variante).join(Producto).filter(
            (Producto.nombre.ilike(f'%{producto_filtro}%')) | 
            (Variante.color.ilike(f'%{producto_filtro}%'))
        )

    # Filtro por fecha
    if fecha_filtro:
        query = query.filter(db.func.date(Movimiento.fecha) == fecha_filtro)

    # Ordenamos por los más recientes
    movimientos = query.order_by(Movimiento.fecha.desc()).all()

    # --- NUEVA LÓGICA DE TOTALES ---
    t_entradas = sum(m.cantidad for m in movimientos if m.tipo == 'ENTRADA')
    t_salidas = sum(m.cantidad for m in movimientos if m.tipo == 'SALIDA')
    balance = t_entradas - t_salidas

    return render_template('historial.html', 
                           movimientos=movimientos, 
                           t_entradas=t_entradas, 
                           t_salidas=t_salidas, 
                           balance=balance)


@inventario_bp.route('/movimiento/<int:variante_id>', methods=['POST'])
@login_required
def registrar_movimiento(variante_id):
    variante = Variante.query.get_or_404(variante_id)
    tipo = request.form.get('tipo') 
    cantidad = int(request.form.get('cantidad'))
    motivo = request.form.get('motivo')

    if tipo == 'ENTRADA':
        variante.stock += cantidad
    elif tipo == 'SALIDA':
        if variante.stock >= cantidad:
            variante.stock -= cantidad
        else:
            flash('Stock insuficiente', 'danger')
            # Redirige de vuelta a la lista si hay error
            return redirect(url_for('inventario.ver_inventario'))

    nuevo_mov = Movimiento(
        variante_id=variante.id,
        usuario_id=current_user.id,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo
    )
    
    db.session.add(nuevo_mov)
    db.session.commit()
    
    flash(f'Movimiento registrado con éxito', 'success')
    return redirect(url_for('inventario.ver_inventario'))