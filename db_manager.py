import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Crear Tablas Básicas
    c.execute('''CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            sala_id TEXT NOT NULL, 
            usuario TEXT NOT NULL, 
            mensaje TEXT NOT NULL, 
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            
    c.execute('''CREATE TABLE IF NOT EXISTS salas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nombre TEXT NOT NULL, 
            geo TEXT NOT NULL, 
            descripcion TEXT)''')
            
    c.execute('''CREATE TABLE IF NOT EXISTS frases (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            categoria TEXT NOT NULL, 
            texto TEXT NOT NULL, 
            autor TEXT DEFAULT 'Anónimo')''')

    # Crear Tabla Reacciones
    c.execute('''CREATE TABLE IF NOT EXISTS reacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensaje_id INTEGER NOT NULL,
            usuario TEXT NOT NULL,
            emoji TEXT NOT NULL
        )''')

    # --- NUEVAS TABLAS PARA SISTEMA ROBUSTO ---

    # Tabla de Usuarios (Soporte para Login y Perfil)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            avatar_url TEXT DEFAULT 'https://api.dicebear.com/7.x/avataaars/svg?seed=default',
            bio TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

    # Tabla de Contactos
    c.execute('''CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(contact_id) REFERENCES users(id),
            UNIQUE(user_id, contact_id)
        )''')

    # Tabla de Bloqueos
    c.execute('''CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            FOREIGN KEY(blocker_id) REFERENCES users(id),
            FOREIGN KEY(blocked_id) REFERENCES users(id),
            UNIQUE(blocker_id, blocked_id)
        )''')
        
    conn.commit()
    conn.close()
    
    check_salas_iniciales()
    check_frases_iniciales()

def check_salas_iniciales():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("SELECT count(*) FROM salas")
        if c.fetchone()[0] == 0:
            print("Creando salas por defecto...")
            salas = [('Tres Valles - General', 'local', 'Chat principal'), 
                     ('Tuxtepec - Amistad', 'cercano', 'Amigos región')]
            c.executemany("INSERT INTO salas (nombre, geo, descripcion) VALUES (?, ?, ?)", salas)
            conn.commit()
    except: pass
    conn.close()

def check_frases_iniciales():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("SELECT count(*) FROM frases")
        if c.fetchone()[0] == 0:
            frases = [('amor', 'El amor no se mira, se siente.', 'Neruda')]
            c.executemany("INSERT INTO frases (categoria, texto, autor) VALUES (?, ?, ?)", frases)
            conn.commit()
    except: pass
    conn.close()

# --- GESTIÓN DE USUARIOS ---

def create_user(username, password, email=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        hashed = generate_password_hash(password)
        avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}&backgroundColor=b6e3f4"
        c.execute("INSERT INTO users (username, password_hash, email, avatar_url) VALUES (?, ?, ?, ?)",
                  (username, hashed, email, avatar))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Usuario duplicado
    finally:
        conn.close()

def get_user_by_username(username):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def verify_user(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

def update_user_profile(user_id, email, bio, avatar_url=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if avatar_url:
        c.execute("UPDATE users SET email = ?, bio = ?, avatar_url = ? WHERE id = ?", (email, bio, avatar_url, user_id))
    else:
        c.execute("UPDATE users SET email = ?, bio = ? WHERE id = ?", (email, bio, user_id))
    conn.commit()
    conn.close()

def search_users(query):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, username, avatar_url, bio FROM users WHERE username LIKE ? LIMIT 10", (f'%{query}%',))
    users = [dict(u) for u in c.fetchall()]
    conn.close()
    return users

# --- CONTACTOS Y BLOQUEOS ---

def add_contact(user_id, contact_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO contacts (user_id, contact_id) VALUES (?, ?)", (user_id, contact_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_contacts(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.username, u.avatar_url, u.bio
        FROM contacts c
        JOIN users u ON c.contact_id = u.id
        WHERE c.user_id = ?
    """, (user_id,))
    contacts = [dict(row) for row in c.fetchall()]
    conn.close()
    return contacts

def block_user(blocker_id, blocked_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO blocks (blocker_id, blocked_id) VALUES (?, ?)", (blocker_id, blocked_id))
        # También eliminar de contactos si existe
        c.execute("DELETE FROM contacts WHERE user_id = ? AND contact_id = ?", (blocker_id, blocked_id))
        c.execute("DELETE FROM contacts WHERE user_id = ? AND contact_id = ?", (blocked_id, blocker_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def is_blocked(user_id, target_id):
    # Verifica si user_id ha bloqueado a target_id O si target_id ha bloqueado a user_id
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM blocks WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)",
              (user_id, target_id, target_id, user_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_blocked_users(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.username, u.avatar_url
        FROM blocks b
        JOIN users u ON b.blocked_id = u.id
        WHERE b.blocker_id = ?
    """, (user_id,))
    blocked = [dict(row) for row in c.fetchall()]
    conn.close()
    return blocked

def unblock_user(blocker_id, blocked_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    conn.commit()
    conn.close()

# --- EXISTING FUNCTIONS (Modified/Kept) ---

def toggle_reaccion(mensaje_id, usuario, emoji):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("SELECT id FROM reacciones WHERE mensaje_id = ? AND usuario = ? AND emoji = ?", (mensaje_id, usuario, emoji))
        existe = c.fetchone()
        
        if existe: 
            c.execute("DELETE FROM reacciones WHERE id = ?", (existe[0],))
        else: 
            c.execute("INSERT INTO reacciones (mensaje_id, usuario, emoji) VALUES (?, ?, ?)", (mensaje_id, usuario, emoji))
            
        conn.commit()
        
        c.execute("SELECT emoji, COUNT(*) FROM reacciones WHERE mensaje_id = ? GROUP BY emoji", (mensaje_id,))
        return dict(c.fetchall())
    except Exception as e:
        print(f"Error reacciones: {e}")
        return {}
    finally:
        conn.close()

def obtener_historial(sala_id, limite=50):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    historial = []
    try:
        c.execute("SELECT id, usuario, mensaje, timestamp FROM mensajes WHERE sala_id = ? ORDER BY id DESC LIMIT ?", (sala_id, limite))
        filas = c.fetchall()
        
        for fila in filas:
            raw = fila['timestamp']
            try: 
                hora = datetime.strptime(raw, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            except: 
                hora = raw[-8:-3] if raw and len(raw) > 8 else datetime.now().strftime('%H:%M')

            reacciones = {}
            try:
                c.execute("SELECT emoji, COUNT(*) FROM reacciones WHERE mensaje_id = ? GROUP BY emoji", (fila['id'],))
                reacciones = dict(c.fetchall())
            except Exception as e: 
                print(f"Error leyendo reacciones msg {fila['id']}: {e}")

            # Obtener avatar del usuario si existe en la tabla users
            avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={fila['usuario']}&backgroundColor=b6e3f4"
            try:
                # Pequeña optimización: Podríamos hacer join arriba, pero por ahora lo hacemos lazy o asumimos default
                # Si quisieramos el avatar real:
                # user_data = get_user_by_username(fila['usuario'])
                # if user_data: avatar = user_data['avatar_url']
                pass
            except: pass

            historial.append({
                'id': fila['id'],
                'username': fila['usuario'],
                'msg': fila['mensaje'],
                'hora': hora,
                'reacciones': reacciones,
                'avatar': avatar # Agregamos avatar al historial
            })
    except Exception as e:
        print(f"Error historial: {e}")
    finally:
        conn.close()
    
    return historial[::-1]

def guardar_mensaje(sala_id, usuario, mensaje):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO mensajes (sala_id, usuario, mensaje) VALUES (?, ?, ?)", (sala_id, usuario, mensaje))
    conn.commit()
    idx = c.lastrowid
    conn.close()
    return idx

def borrar_mensaje_db(msg_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM mensajes WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

def obtener_salas():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM salas")
    r = [dict(f) for f in c.fetchall()]
    conn.close()
    return r

def obtener_sala_info(sala_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM salas WHERE id = ?", (sala_id,))
    r = c.fetchone()
    conn.close()
    return dict(r) if r else None

def crear_nueva_sala(n, g, d):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO salas (nombre, geo, descripcion) VALUES (?, ?, ?)", (n, g, d))
    conn.commit()
    conn.close()

def obtener_categorias_frases():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT categoria, COUNT(*) FROM frases GROUP BY categoria")
    r = c.fetchall()
    conn.close()
    return r

def obtener_frases_por_categoria(cat):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM frases WHERE categoria = ?", (cat,))
    r = [dict(f) for f in c.fetchall()]
    conn.close()
    return r

def agregar_frase(c, t, a):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO frases (categoria, texto, autor) VALUES (?, ?, ?)", (c, t, a))
    conn.commit()
    conn.close()