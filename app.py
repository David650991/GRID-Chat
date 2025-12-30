from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import db_manager
from datetime import datetime

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

@app.route('/static/sw.js')
def sw():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

# --- SOCKET.IO ---

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

# NUEVO: Evento connect para enviar datos iniciales inmediatamente
@socketio.on('connect')
def handle_connect():
    # Solo confirmación de conexión, la lógica de sala va en 'join'
    pass

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    sid = request.sid
    join_room(room)
    
    # Registramos usuario
    USUARIOS_ACTIVOS[sid] = {'nick': username, 'sala': room}
    
    # 1. Enviar historial al usuario que entra
    historial = db_manager.obtener_historial(room)
    emit('historial_previo', historial, to=sid)
    
    # 2. Avisar a la sala
    send(f'{username} ha entrado a la sala.', to=room)
    
    # 3. Actualizar lista de usuarios (ESTO SE REPARA AHORA)
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
        
        # Eliminamos usuario ANTES de avisar
        del USUARIOS_ACTIVOS[sid]
        
        send(f'{nick} ha salido de la sala.', to=room)
        emitir_lista_usuarios(room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    msg = data['msg']
    username = data['username']
    
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
    # Filtramos usuarios que están en ESTA sala específica
    lista = [u['nick'] for u in USUARIOS_ACTIVOS.values() if u['sala'] == sala_id]
    # Eliminamos duplicados (si alguien tiene 2 pestañas abiertas con el mismo nombre)
    lista_unica = list(set(lista))
    socketio.emit('update_users', lista_unica, to=sala_id)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)