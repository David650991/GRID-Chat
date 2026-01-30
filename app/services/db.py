import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "chat_history.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Core Tables
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

    c.execute('''CREATE TABLE IF NOT EXISTS reacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensaje_id INTEGER NOT NULL,
            usuario TEXT NOT NULL,
            emoji TEXT NOT NULL
        )''')

    # Auth & Social Tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            avatar_url TEXT DEFAULT 'https://api.dicebear.com/7.x/avataaars/svg?seed=default',
            bio TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

    c.execute('''CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(contact_id) REFERENCES users(id),
            UNIQUE(user_id, contact_id)
        )''')

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

    # Seed data
    _check_initial_data()

def _check_initial_data():
    conn = get_db_connection()
    c = conn.cursor()

    # Salas
    c.execute("SELECT count(*) FROM salas")
    if c.fetchone()[0] == 0:
        salas = [('Tres Valles - General', 'local', 'Chat principal'),
                 ('Tuxtepec - Amistad', 'cercano', 'Amigos región')]
        c.executemany("INSERT INTO salas (nombre, geo, descripcion) VALUES (?, ?, ?)", salas)

    # Frases
    c.execute("SELECT count(*) FROM frases")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO frases (categoria, texto, autor) VALUES (?, ?, ?)",
                  ('amor', 'El amor no se mira, se siente.', 'Neruda'))

    conn.commit()
    conn.close()

# --- USER REPO ---
def create_user(username, password, email=None):
    conn = get_db_connection()
    try:
        hashed = generate_password_hash(password)
        avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}&backgroundColor=b6e3f4"
        conn.execute("INSERT INTO users (username, password_hash, email, avatar_url) VALUES (?, ?, ?, ?)",
                  (username, hashed, email, avatar))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def update_user_profile(user_id, email, bio, avatar_url=None):
    conn = get_db_connection()
    if avatar_url:
        conn.execute("UPDATE users SET email = ?, bio = ?, avatar_url = ? WHERE id = ?", (email, bio, avatar_url, user_id))
    else:
        conn.execute("UPDATE users SET email = ?, bio = ? WHERE id = ?", (email, bio, user_id))
    conn.commit()
    conn.close()

def search_users(query):
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, avatar_url, bio FROM users WHERE username LIKE ? LIMIT 10", (f'%{query}%',)).fetchall()
    conn.close()
    return [dict(u) for u in users]

# --- SOCIAL REPO ---
def add_contact(user_id, contact_id):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO contacts (user_id, contact_id) VALUES (?, ?)", (user_id, contact_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_contacts(user_id):
    conn = get_db_connection()
    res = conn.execute("""
        SELECT u.id, u.username, u.avatar_url, u.bio
        FROM contacts c
        JOIN users u ON c.contact_id = u.id
        WHERE c.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in res]

def block_user(blocker_id, blocked_id):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO blocks (blocker_id, blocked_id) VALUES (?, ?)", (blocker_id, blocked_id))
        conn.execute("DELETE FROM contacts WHERE user_id = ? AND contact_id = ?", (blocker_id, blocked_id))
        conn.execute("DELETE FROM contacts WHERE user_id = ? AND contact_id = ?", (blocked_id, blocker_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_blocked_users(user_id):
    conn = get_db_connection()
    res = conn.execute("""
        SELECT u.id, u.username, u.avatar_url
        FROM blocks b
        JOIN users u ON b.blocked_id = u.id
        WHERE b.blocker_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in res]

# --- CHAT REPO ---
def get_rooms():
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM salas").fetchall()
    conn.close()
    return [dict(r) for r in res]

def get_room_by_id(sala_id):
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM salas WHERE id = ?", (sala_id,)).fetchone()
    conn.close()
    return dict(res) if res else None

def create_room(nombre, geo, desc):
    conn = get_db_connection()
    conn.execute("INSERT INTO salas (nombre, geo, descripcion) VALUES (?, ?, ?)", (nombre, geo, desc))
    conn.commit()
    conn.close()

def save_message(sala_id, usuario, mensaje):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO mensajes (sala_id, usuario, mensaje) VALUES (?, ?, ?)", (sala_id, usuario, mensaje))
    conn.commit()
    msg_id = c.lastrowid
    conn.close()
    return msg_id

def delete_message(msg_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM mensajes WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

def get_history(sala_id, limit=50):
    conn = get_db_connection()
    try:
        msgs = conn.execute("SELECT id, usuario, mensaje, timestamp FROM mensajes WHERE sala_id = ? ORDER BY id DESC LIMIT ?", (sala_id, limit)).fetchall()
        result = []
        for row in msgs:
            msg = dict(row)
            # Time format
            raw = msg['timestamp']
            try:
                msg['hora'] = datetime.strptime(raw, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            except:
                msg['hora'] = raw[-8:-3] if raw and len(raw)>8 else '??:??'

            # Reactions
            reacs = conn.execute("SELECT emoji, COUNT(*) FROM reacciones WHERE mensaje_id = ? GROUP BY emoji", (msg['id'],)).fetchall()
            msg['reacciones'] = dict(reacs)

            # Avatar (Lazy fetch)
            msg['avatar'] = f"https://api.dicebear.com/7.x/avataaars/svg?seed={msg['usuario']}&backgroundColor=b6e3f4"

            result.append(msg)
        return result[::-1]
    finally:
        conn.close()

def toggle_reaction(msg_id, user, emoji):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        existe = c.execute("SELECT id FROM reacciones WHERE mensaje_id = ? AND usuario = ? AND emoji = ?", (msg_id, user, emoji)).fetchone()
        if existe:
            c.execute("DELETE FROM reacciones WHERE id = ?", (existe['id'],))
        else:
            c.execute("INSERT INTO reacciones (mensaje_id, usuario, emoji) VALUES (?, ?, ?)", (msg_id, user, emoji))
        conn.commit()

        counts = c.execute("SELECT emoji, COUNT(*) FROM reacciones WHERE mensaje_id = ? GROUP BY emoji", (msg_id,)).fetchall()
        return dict(counts)
    finally:
        conn.close()

# --- FRASES REPO ---
def get_phrase_categories():
    conn = get_db_connection()
    res = conn.execute("SELECT categoria, COUNT(*) FROM frases GROUP BY categoria").fetchall()
    conn.close()
    return res

def get_phrases_by_cat(cat):
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM frases WHERE categoria = ?", (cat,)).fetchall()
    conn.close()
    return [dict(r) for r in res]

def add_phrase(cat, text, author):
    conn = get_db_connection()
    conn.execute("INSERT INTO frases (categoria, texto, autor) VALUES (?, ?, ?)", (cat, text, author))
    conn.commit()
    conn.close()
