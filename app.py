from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import db_manager
from datetime import datetime
import os
import random
from functools import wraps

app = Flask(__name__)
# SECURITY CONFIGURATION
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_atomica_v2') # Change in production
# app.config['SESSION_COOKIE_HTTPONLY'] = True
# app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# app.config['SESSION_COOKIE_SECURE'] = True # Uncomment in production with HTTPS

socketio = SocketIO(app, cors_allowed_origins="*")

db_manager.init_db()

USUARIOS_ACTIVOS = {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS DE NAVEGACIÓN ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    lista_salas = db_manager.obtener_salas()
    es_admin = session.get('es_admin', False)
    # Obtenemos datos frescos del usuario
    user = db_manager.get_user_by_id(session['user_id'])

    return render_template('index.html',
                           salas=lista_salas,
                           es_admin=es_admin,
                           user=user)

# --- AUTENTICACIÓN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = db_manager.verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['avatar_url'] = user['avatar_url']
            session['es_admin'] = (username == 'admin') # Simple admin check logic
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html', mode='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        if db_manager.create_user(username, password, email):
            flash('Cuenta creada con éxito. Por favor inicia sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('El nombre de usuario ya existe.', 'error')

    return render_template('login.html', mode='register')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ADMIN ---

@app.route('/admin')
def admin_page():
    if session.get('es_admin'):
        return redirect(url_for('index'))
    return render_template('login.html', mode='admin') # Reusamos login.html

@app.route('/login_admin', methods=['POST'])
def admin_login():
    password = request.form.get('password')
    admin_secret = os.environ.get('ADMIN_PASSWORD', 'admin123') # Default only for dev

    if password and password == admin_secret:
        session['es_admin'] = True
        session['nick'] = 'Administrador'
        flash('¡Bienvenido, Jefe!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Credenciales inválidas', 'error')
        return redirect(url_for('admin_page'))

@app.route('/crear_sala', methods=['POST'])
def create_room():
    if not session.get('es_admin'):
        return "Acceso Denegado", 403

    nombre = request.form.get('nombre', '').strip()
    geo = request.form.get('geo', 'local')
    desc = request.form.get('descripcion', '').strip()

    if len(nombre) > 2 and len(nombre) < 50:
        db_manager.crear_nueva_sala(nombre, geo, desc)
        flash('Sala creada exitosamente.', 'success')
    else:
        flash('Error: Nombre de sala inválido.', 'error')

    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', content=f"<div style='text-align:center; padding:50px;'><h1>404</h1><p>Recurso no encontrado.</p><a href='/'>Volver al inicio</a></div>"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('base.html', content=f"<div style='text-align:center; padding:50px;'><h1>500</h1><p>Error interno del sistema.</p><a href='/'>Volver al inicio</a></div>"), 500

@app.route('/chat/<sala_id>')
@login_required
def chat(sala_id):
    info_sala = db_manager.obtener_sala_info(sala_id)
    if not info_sala:
        return redirect(url_for('index'))

    user = db_manager.get_user_by_id(session['user_id'])
    es_admin = session.get('es_admin', False)

    return render_template('chat.html',
                           sala_id=sala_id,
                           info_sala=info_sala,
                           user=user,
                           es_admin=es_admin)

# --- API ENDPOINTS (AJAX) ---

@app.route('/api/search_users')
@login_required
def search_users_api():
    query = request.args.get('q', '')
    if len(query) < 2: return jsonify([])
    users = db_manager.search_users(query)
    # Filtramos al propio usuario
    users = [u for u in users if u['id'] != session['user_id']]
    return jsonify(users)

@app.route('/api/contacts')
@login_required
def get_contacts_api():
    contacts = db_manager.get_contacts(session['user_id'])
    return jsonify(contacts)

@app.route('/api/add_contact', methods=['POST'])
@login_required
def add_contact_api():
    data = request.json
    target_id = data.get('user_id')
    if db_manager.add_contact(session['user_id'], target_id):
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

@app.route('/api/block_user', methods=['POST'])
@login_required
def block_user_api():
    data = request.json
    target_id = data.get('user_id')
    if db_manager.block_user(session['user_id'], target_id):
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

@app.route('/api/blocked_users')
@login_required
def get_blocked_users_api():
    blocked = db_manager.get_blocked_users(session['user_id'])
    return jsonify(blocked)

@app.route('/api/update_profile', methods=['POST'])
@login_required
def update_profile_api():
    data = request.json
    email = data.get('email')
    bio = data.get('bio')
    avatar = data.get('avatar_url')

    db_manager.update_user_profile(session['user_id'], email, bio, avatar)
    return jsonify({'status': 'ok'})

# --- FRASES (LEGACY) ---

@app.route('/frases')
def frases_index():
    categorias = db_manager.obtener_categorias_frases()
    es_admin = session.get('es_admin', False)
    return render_template('frases.html', categorias=categorias, es_admin=es_admin)

@app.route('/frases/<categoria>')
def frases_categoria(categoria):
    frases = db_manager.obtener_frases_por_categoria(categoria)
    es_admin = session.get('es_admin', False)
    return render_template('frases_detalle.html', categoria=categoria, frases=frases, es_admin=es_admin)

@app.route('/agregar_frase', methods=['POST'])
def add_phrase():
    if not session.get('es_admin'):
        return "Acceso Denegado", 403

    categoria = request.form.get('categoria').lower()
    texto = request.form.get('texto')
    autor = request.form.get('autor')

    if categoria and texto:
        db_manager.agregar_frase(categoria, texto, autor)
        flash('Frase agregada correctamente')

    return redirect(url_for('frases_index'))

# --- RUTAS PWA ---
@app.route('/sw.js')
def service_worker():
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache' 
    return response

@app.route('/static/sw.js')
def static_service_worker():
    return service_worker()

@app.route('/manifest.json')
def manifest():
    response = make_response(send_from_directory('static', 'manifest.json'))
    response.headers['Content-Type'] = 'application/manifest+json'
    return response

# --- SOCKET.IO ---

@socketio.on('reaccionar')
def handle_reaction(data):
    msg_id = data['id']
    emoji = data['emoji']
    room = data['room']
    username = session.get('username', 'Anónimo')
    
    nuevos_conteos = db_manager.toggle_reaccion(msg_id, username, emoji)
    
    emit('actualizar_reacciones', {
        'id': msg_id,
        'reacciones': nuevos_conteos
    }, to=room)

@socketio.on('join')
def on_join(data):
    room = data['room']
    sid = request.sid
    
    # Validar sesión
    if 'user_id' not in session:
        emit('error_auth', {'mensaje': 'No autenticado'}, to=sid)
        return

    username = session['username']
    user_id = session['user_id']

    join_room(room)
    
    USUARIOS_ACTIVOS[sid] = {'nick': username, 'sala': room, 'id': user_id}
    
    historial = db_manager.obtener_historial(room)
    emit('historial_previo', historial, to=sid)
    
    send(f'{username} ha entrado a la sala.', to=room)
    emitir_lista_usuarios(room)

@socketio.on('typing')
def handle_typing(data):
    room = data['room']
    username = session.get('username')
    if username:
        emit('display_typing', {'username': username}, to=room, include_self=False)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    if sid in USUARIOS_ACTIVOS:
        user_data = USUARIOS_ACTIVOS[sid]
        room = user_data['sala']
        nick = user_data['nick']
        del USUARIOS_ACTIVOS[sid]
        
        send(f'{nick} ha salido de la sala.', to=room)
        emitir_lista_usuarios(room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    msg = data['msg']

    if 'user_id' not in session:
        return

    username = session['username']
    
    msg_id = db_manager.guardar_mensaje(room, username, msg)
    hora_actual = datetime.now().strftime('%H:%M')

    # Obtenemos avatar fresco
    avatar = session.get('avatar_url', f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}&backgroundColor=b6e3f4")
    user_id = session.get('user_id')

    send({'id': msg_id, 'msg': msg, 'username': username, 'user_id': user_id, 'hora': hora_actual, 'avatar': avatar}, to=room)

@socketio.on('borrar_mensaje')
def handle_delete(data):
    msg_id = data['id']
    room = data['room']
    # Aquí podríamos añadir validación de propiedad del mensaje
    db_manager.borrar_mensaje_db(msg_id)
    emit('mensaje_eliminado', {'id': msg_id}, to=room)

def emitir_lista_usuarios(sala_id):
    # Ahora enviamos objetos más completos
    lista = []
    ids_procesados = set()

    for u in USUARIOS_ACTIVOS.values():
        if u['sala'] == sala_id and u['id'] not in ids_procesados:
            # Recuperamos avatar de la DB o sesión si fuera posible, por ahora simulamos con DB
            user_db = db_manager.get_user_by_id(u['id'])
            avatar = user_db['avatar_url'] if user_db else ""

            lista.append({
                'username': u['nick'],
                'avatar': avatar,
                'id': u['id']
            })
            ids_procesados.add(u['id'])

    socketio.emit('update_users', lista, to=sala_id)

# --- SEO Y SEGURIDAD ---

@app.route('/robots.txt')
def robots():
    base_url = "https://grid-chat-lknf.onrender.com" 
    content = f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml"
    return content, 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    base_url = "https://grid-chat-lknf.onrender.com"
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>{base_url}/</loc>
            <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>
        <url>
            <loc>{base_url}/frases</loc>
            <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
            <changefreq>weekly</changefreq>
            <priority>0.8</priority>
        </url>
    </urlset>'''
    return xml, 200, {'Content-Type': 'application/xml'}

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if response.headers.get('Content-Type') == 'application/javascript':
        response.headers['Service-Worker-Allowed'] = '/'
    return response

if __name__ == '__main__':
    socketio.run(app, debug=False, port=5000)