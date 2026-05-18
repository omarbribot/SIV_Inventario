import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Categoria, Producto, Variante, Movimiento
from PIL import Image
from sqlalchemy.orm import joinedload
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
            flash('Categoría creada con éxito.', 'success')
   
    # Usando select compatible con SQLAlchemy 2.0
    todas = db.session.scalars(db.select(Categoria)).all()
    return render_template('categorias.html', categorias=todas)

@inventario_bp.route('/productos')
@login_required
def ver_inventario():
    categoria_id = request.args.get('categoria_id')
    
    # Consulta base adaptada
    stmt = db.select(Producto)
    if categoria_id:
        stmt = stmt.filter_by(categoria_id=categoria_id)
    
    productos = db.session.scalars(stmt).all()
    categorias = db.session.scalars(db.select(Categoria)).all()
    
    return render_template('inventario.html', productos=productos, categorias=categorias)

@inventario_bp.route('/producto/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_producto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        categoria_id = request.form.get('categoria_id')
        descripcion = request.form.get('descripcion')

        # 1. Crear el producto base (sin imagen global)
        nuevo_p = Producto(
            nombre=nombre,
            categoria_id=categoria_id,
            descripcion=descripcion
        )
        db.session.add(nuevo_p)
        db.session.flush()  # Genera el ID de nuevo_p sin cerrar la transacción

        # 2. Capturar las listas de las variantes (incluyendo sus fotos)
        tallas = request.form.getlist('talla[]')
        colores = request.form.getlist('color[]')
        stocks = request.form.getlist('stock[]')
        precios = request.form.getlist('precio[]')
        fotos = request.files.getlist('foto_variante[]') # Array con las fotos individuales

        # 3. Guardar cada variante procesando su respectiva foto
        limite_iteracion = max(len(tallas), len(colores), len(stocks), len(precios))

        for i in range(limite_iteracion):
            talla_val = tallas[i] if i < len(tallas) else ""
            color_val = colores[i] if i < len(colores) else ""
            stock_raw = stocks[i] if i < len(stocks) else "0"
            precio_raw = precios[i] if i < len(precios) else "0"
            
            # Capturar el archivo correspondiente a esta variante específica
            file = fotos[i] if i < len(fotos) else None
            filename = 'default.png'

            # Validamos que al menos tenga algún dato para guardar la variante
            if talla_val or color_val or precio_raw:
                stock_inicial = int(stock_raw if stock_raw.isdigit() else 0)
                
                try:
                    precio_venta = float(precio_raw) if precio_raw else 0.0
                except ValueError:
                    precio_venta = 0.0

                # --- Lógica de Optimización con Pillow para cada variante individual ---
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    # Para evitar colisiones de nombres si suben la misma foto en variantes distintas, 
                    # le concatenamos el índice o propiedades únicos
                    base, ext = os.path.splitext(filename)
                    filename = f"{nuevo_p.id}_{i}_{secure_filename(base)}.jpg"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    
                    try:
                        img = Image.open(file)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        
                        max_size = (800, 800)
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        img.save(filepath, "JPEG", quality=75)
                        
                    except Exception as e:
                        file.seek(0)
                        file.save(filepath)
                        flash(f'La foto de la variante {i+1} se guardó sin optimizar.', 'warning')

                # Crear el registro de la variante con su foto correspondiente
                v = Variante(
                    producto_id=nuevo_p.id,
                    talla=talla_val if talla_val else "N/A",
                    color=color_val if color_val else "General",
                    stock=stock_inicial,
                    precio_venta=precio_venta,
                    imagen=filename # Guardamos el nombre del archivo en la variante
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

        # --- Lógica de redirección ---
        accion = request.form.get('accion')
        if accion == 'finalizar':
            flash(f'Producto "{nombre}" y sus variantes guardados con éxito.', 'success')
            return redirect(url_for('inventario.ver_inventario'))
        else:
            flash(f'¡{nombre} registrado con éxito! Listo para el siguiente.', 'success')
            return redirect(url_for('inventario.nuevo_producto'))

    categorias = db.session.scalars(db.select(Categoria)).all()
    return render_template('nuevo_producto.html', categorias=categorias)

@inventario_bp.route('/historial')
@login_required
def ver_historial():
    fecha_filtro = request.args.get('fecha')
    producto_filtro = request.args.get('producto')

    # Consulta base adaptada
    stmt = db.select(Movimiento).options(
        joinedload(Movimiento.variante).joinedload(Variante.producto)
    )
    if producto_filtro:
        stmt = stmt.join(Movimiento.variante).join(Variante.producto).filter(
            (Producto.nombre.ilike(f'%{producto_filtro}%')) |
            (Variante.color.ilike(f'%{producto_filtro}%'))
        )

    if fecha_filtro:
        stmt = stmt.filter(db.func.date(Movimiento.fecha) == fecha_filtro)

    movimientos = db.session.scalars(stmt.order_by(Movimiento.fecha.desc())).all()

    # Totales
    t_entradas = sum(m.cantidad for m in movimientos if m.tipo == 'ENTRADA')
    t_salidas = sum(m.cantidad for m in movimientos if m.tipo == 'SALIDA')
    balance = t_entradas - t_salidas

    return render_template('historial.html',
                           movimientos=movimientos,
                           t_entradas=t_entradas,
                           t_salidas=t_salidas,
                           balance=balance)
@inventario_bp.route('/producto/editar/<int:producto_id>', methods=['POST'])
@login_required
def editar_producto(producto_id):
    producto = db.session.get(Producto, producto_id)
    if not producto:
        flash('El producto no existe.', 'danger')
        return redirect(url_for('inventario.ver_inventario'))

    # Capturamos los campos editables seguros
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')

    if not nombre:
        flash('El nombre del producto no puede estar vacío.', 'danger')
        return redirect(url_for('inventario.ver_inventario'))

    producto.nombre = nombre
    producto.descripcion = descripcion

    # --- Lógica de actualización de Imagen con Pillow ---
    file = request.files.get('imagen')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        try:
            img = Image.open(file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Redimensionamos al mismo estándar de 800px
            max_size = (800, 800)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(filepath, "JPEG", quality=75)
            
            # Si la foto anterior no era la por defecto, podríamos borrarla, 
            # pero por ahora simplemente asignamos el nuevo nombre para evitar conflictos
            producto.imagen = filename
            
        except Exception as e:
            file.seek(0)
            file.save(filepath)
            producto.imagen = filename
            flash('La imagen se actualizó en formato original sin optimizar.', 'warning')

    db.session.commit()
    flash(f'Producto "{producto.nombre}" actualizado correctamente.', 'success')
    return redirect(url_for('inventario.ver_inventario'))

@inventario_bp.route('/movimiento/<int:variante_id>', methods=['POST'])
@login_required
def registrar_movimiento(variante_id):
    # Corrección para compatibilidad
    variante = db.session.get(Variante, variante_id)
    if not variante:
        flash('La variante no existe.', 'danger')
        return redirect(url_for('inventario.ver_inventario'))

    tipo = request.form.get('tipo')
    cantidad_raw = request.form.get('cantidad')
    motivo = request.form.get('motivo')

    # Validación de conversión segura
    if not cantidad_raw or not cantidad_raw.isdigit():
        flash('Cantidad inválida introducida.', 'danger')
        return redirect(url_for('inventario.ver_inventario'))
        
    cantidad = int(cantidad_raw)

    if tipo == 'ENTRADA':
        variante.stock += cantidad
    elif tipo == 'SALIDA':
        if variante.stock >= cantidad:
            variante.stock -= cantidad
        else:
            flash(f'Stock insuficiente para extraer unidades de esta variante.', 'danger')
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
    
    flash('Movimiento de inventario procesado.', 'success')
    return redirect(url_for('inventario.ver_inventario'))