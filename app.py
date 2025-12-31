from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import db_manager
from datetime import datetime
import os

app = Flask(__name__)
# IMPORTANTE: Esta clave cifra las cookies. En producción debe ser muy compleja.
app.config['SECRET_KEY'] = 'super_secreto_atomico_v2'
socketio = SocketIO(app)

db_manager.init_db()

USUARIOS_ACTIVOS = {}
ADMIN_PASSWORD = "12345"

# --- RUTAS DE NAVEGACIÓN ---

@app.route('/')
def index():
    lista_salas = db_manager.obtener_salas()
    es_admin = session.get('es_admin', False)
    nick_guardado = session.get('nick', '')

    return render_template('index.html',
                           salas=lista_salas,
                           es_admin=es_admin,
                           nick_guardado=nick_guardado)

@app.route('/admin')
def admin_page():
    if session.get('es_admin'):
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/login_admin', methods=['POST'])
def admin_login():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['es_admin'] = True
        session['nick'] = 'Administrador'
        flash('¡Bienvenido, Jefe!')
        return redirect(url_for('index'))
    else:
        flash('Contraseña incorrecta')
        return redirect(url_for('admin_page'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/crear_sala', methods=['POST'])
def create_room():
    if not session.get('es_admin'):
        return "Acceso Denegado", 403

    nombre = request.form.get('nombre')
    geo = request.form.get('geo')
    desc = request.form.get('descripcion')

    if nombre and geo:
        db_manager.crear_nueva_sala(nombre, geo, desc)

    return redirect(url_for('index'))

@app.route('/chat/<sala_id>')
def chat(sala_id):
    info_sala = db_manager.obtener_sala_info(sala_id)
    if not info_sala:
        return redirect(url_for('index'))

    nick_url = request.args.get('nick')
    if nick_url:
        session['nick'] = nick_url

    nickname = session.get('nick', 'Anónimo')
    es_admin = session.get('es_admin', False)

    return render_template('chat.html',
                           sala_id=sala_id,
                           info_sala=info_sala,
                           nickname=nickname,
                           es_admin=es_admin)

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

def generar_nick_unico(room, base_nick):
    # Obtener nicks actuales en la sala
    nicks_en_sala = [u['nick'] for u in USUARIOS_ACTIVOS.values() if u['sala'] == room]
    
    # Proteger el nick de Administrador
    if base_nick.lower() == "administrador":
        # Si intenta ser admin pero no tiene la sesión de admin, le cambiamos el nombre
        # Accedemos a la sesión dentro del contexto de socketio (request context)
        # Nota: Flask-SocketIO maneja contextos, pero session puede ser tricky. 
        # Simplificamos: Si el nick base es Admin y ya hay uno, o no es admin real...
        pass 

    nuevo_nick = base_nick
    contador = 1
    while nuevo_nick in nicks_en_sala:
        nuevo_nick = f"{base_nick}_{contador}"
        contador += 1
    return nuevo_nick

@socketio.on('reaccionar')
def handle_reaction(data):
    msg_id = data['id']
    emoji = data['emoji']
    room = data['room']
    username = data['username']
    
    nuevos_conteos = db_manager.toggle_reaccion(msg_id, username, emoji)
    
    emit('actualizar_reacciones', {
        'id': msg_id,
        'reacciones': nuevos_conteos
    }, to=room)

@socketio.on('connect')
def handle_connect():
    pass

@socketio.on('join')
def on_join(data):
    username_solicitado = data['username']
    room = data['room']
    sid = request.sid
    
    # 1. Lógica de Nick Único
    username_final = generar_nick_unico(room, username_solicitado)
    
    # Si intentan usar "Administrador" sin permiso, forzamos cambio (opcional, aqui solo evitamos duplicados)
    # Pero si ya existe un "Administrador", el generar_nick_unico lo volverá "Administrador_1"
    
    join_room(room)
    
    # Guardamos el nick final
    USUARIOS_ACTIVOS[sid] = {'nick': username_final, 'sala': room}
    
    # Avisamos al usuario su nombre final (por si cambió)
    emit('set_username', {'username': username_final}, to=sid)
    
    historial = db_manager.obtener_historial(room)
    emit('historial_previo', historial, to=sid)
    
    send(f'{username_final} ha entrado a la sala.', to=room)
    emitir_lista_usuarios(room)

@socketio.on('typing')
def handle_typing(data):
    room = data['room']
    username = data['username']
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
    # Usamos el username que nos manda el cliente (que ya debe estar actualizado)
    # O mejor, usamos el de la sesión activa para evitar hackeos de identidad
    sid = request.sid
    if sid in USUARIOS_ACTIVOS:
        username = USUARIOS_ACTIVOS[sid]['nick']
    else:
        username = data['username'] # Fallback
    
    msg_id = db_manager.guardar_mensaje(room, username, msg)
    hora_actual = datetime.now().strftime('%H:%M')

    send({'id': msg_id, 'msg': msg, 'username': username, 'hora': hora_actual}, to=room)

@socketio.on('borrar_mensaje')
def handle_delete(data):
    msg_id = data['id']
    room = data['room']
    db_manager.borrar_mensaje_db(msg_id)
    emit('mensaje_eliminado', {'id': msg_id}, to=room)

def emitir_lista_usuarios(sala_id):
    lista = [u['nick'] for u in USUARIOS_ACTIVOS.values() if u['sala'] == sala_id]
    lista_unica = list(set(lista))
    socketio.emit('update_users', lista_unica, to=sala_id)

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
    socketio.run(app, debug=True, port=5000)