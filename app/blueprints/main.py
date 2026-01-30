from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
import app.services.db as db

bp = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    lista_salas = db.get_rooms()
    es_admin = session.get('es_admin', False)
    user = db.get_user_by_id(session['user_id'])

    return render_template('index.html', salas=lista_salas, es_admin=es_admin, user=user)

@bp.route('/crear_sala', methods=['POST'])
def create_room():
    if not session.get('es_admin'):
        return "Acceso Denegado", 403

    nombre = request.form.get('nombre', '').strip()
    geo = request.form.get('geo', 'local')
    desc = request.form.get('descripcion', '').strip()

    if len(nombre) > 2 and len(nombre) < 50:
        db.create_room(nombre, geo, desc)
        flash('Sala creada exitosamente.', 'success')
    else:
        flash('Error: Nombre de sala inválido.', 'error')

    return redirect(url_for('main.index'))

@bp.route('/frases')
def frases_index():
    categorias = db.get_phrase_categories()
    es_admin = session.get('es_admin', False)
    return render_template('frases.html', categorias=categorias, es_admin=es_admin)

@bp.route('/frases/<categoria>')
def frases_categoria(categoria):
    frases = db.get_phrases_by_cat(categoria)
    es_admin = session.get('es_admin', False)
    return render_template('frases_detalle.html', categoria=categoria, frases=frases, es_admin=es_admin)

@bp.route('/agregar_frase', methods=['POST'])
def add_phrase():
    if not session.get('es_admin'):
        return "Acceso Denegado", 403

    categoria = request.form.get('categoria').lower()
    texto = request.form.get('texto')
    autor = request.form.get('autor')

    if categoria and texto:
        db.add_phrase(categoria, texto, autor)
        flash('Frase agregada correctamente', 'success')

    return redirect(url_for('main.frases_index'))
