from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_temporal_atomica'
socketio = SocketIO(app)

# --- DATOS SEMILLA (SIMULANDO BD) ---
# Centrado en 18.242801, -96.145042 (Tres Valles)
SALAS = {
    '1': {'nombre': 'Tres Valles - General', 'geo': 'local', 'usuarios': 0},
    '2': {'nombre': 'Tuxtepec - Amistad', 'geo': 'cercano', 'usuarios': 0},
    '3': {'nombre': 'Veracruz - Puerto', 'geo': 'regional', 'usuarios': 0},
    '4': {'nombre': 'Cosamaloapan - Charla', 'geo': 'cercano', 'usuarios': 0}
}

@app.route('/')
def index():
    # En el futuro aquí filtraremos por coordenadas reales del usuario
    return render_template('index.html', salas=SALAS)

@app.route('/chat/<sala_id>')
def chat(sala_id):
    if sala_id not in SALAS:
        return redirect(url_for('index'))
    return render_template('chat.html', sala_id=sala_id, info_sala=SALAS[sala_id])

# --- EVENTOS SOCKET.IO (TIEMPO REAL) ---
@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send(f'{username} ha entrado a la sala.', to=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    msg = data['msg']
    username = data['username']
    send(f'{username}: {msg}', to=room)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
