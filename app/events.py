from flask import session, request
from flask_socketio import join_room, leave_room, send, emit
from datetime import datetime
import app.services.db as db

USUARIOS_ACTIVOS = {}

def register_events(socketio):

    @socketio.on('reaccionar')
    def handle_reaction(data):
        msg_id = data['id']
        emoji = data['emoji']
        room = data['room']
        username = session.get('username', 'Anónimo')

        nuevos_conteos = db.toggle_reaction(msg_id, username, emoji)

        emit('actualizar_reacciones', {
            'id': msg_id,
            'reacciones': nuevos_conteos
        }, to=room)

    @socketio.on('join')
    def on_join(data):
        room = data['room']
        sid = request.sid

        if 'user_id' not in session:
            emit('error_auth', {'mensaje': 'No autenticado'}, to=sid)
            return

        username = session['username']
        user_id = session['user_id']

        join_room(room)

        USUARIOS_ACTIVOS[sid] = {'nick': username, 'sala': room, 'id': user_id}

        historial = db.get_history(room)
        emit('historial_previo', historial, to=sid)

        # System message (optional, maybe distracting in dark core?)
        # send(f'{username} ha entrado a la sala.', to=room)
        emitir_lista_usuarios(socketio, room)

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
            del USUARIOS_ACTIVOS[sid]
            emitir_lista_usuarios(socketio, room)

    @socketio.on('message')
    def handle_message(data):
        room = data['room']
        msg = data['msg']

        if 'user_id' not in session:
            return

        username = session['username']

        msg_id = db.save_message(room, username, msg)
        hora_actual = datetime.now().strftime('%H:%M')

        avatar = session.get('avatar_url', f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}&backgroundColor=b6e3f4")
        user_id = session.get('user_id')

        send({'id': msg_id, 'msg': msg, 'username': username, 'user_id': user_id, 'hora': hora_actual, 'avatar': avatar}, to=room)

    @socketio.on('borrar_mensaje')
    def handle_delete(data):
        msg_id = data['id']
        room = data['room']
        # Validar ownership en futuro
        db.delete_message(msg_id)
        emit('mensaje_eliminado', {'id': msg_id}, to=room)

def emitir_lista_usuarios(socketio, sala_id):
    lista = []
    ids_procesados = set()

    for u in USUARIOS_ACTIVOS.values():
        if u['sala'] == sala_id and u['id'] not in ids_procesados:
            user_db = db.get_user_by_id(u['id'])
            avatar = user_db['avatar_url'] if user_db else ""

            lista.append({
                'username': u['nick'],
                'avatar': avatar,
                'id': u['id']
            })
            ids_procesados.add(u['id'])

    socketio.emit('update_users', lista, to=sala_id)
