import sqlite3
from datetime import datetime

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

def toggle_reaccion(mensaje_id, usuario, emoji):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # CORRECCIÓN: Consulta en una sola línea o con triple comilla correcta
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
        # Recuperamos mensajes
        c.execute("SELECT id, usuario, mensaje, timestamp FROM mensajes WHERE sala_id = ? ORDER BY id DESC LIMIT ?", (sala_id, limite))
        filas = c.fetchall()
        
        for fila in filas:
            raw = fila['timestamp']
            try: 
                # Intentamos parsear fecha completa, si falla (o es None) fallback
                hora = datetime.strptime(raw, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            except: 
                # Fallback simple si el formato es distinto
                hora = raw[-8:-3] if raw and len(raw) > 8 else datetime.now().strftime('%H:%M')

            reacciones = {}
            try:
                # CORRECCIÓN: Consulta SQL arreglada
                c.execute("SELECT emoji, COUNT(*) FROM reacciones WHERE mensaje_id = ? GROUP BY emoji", (fila['id'],))
                reacciones = dict(c.fetchall())
            except Exception as e: 
                print(f"Error leyendo reacciones msg {fila['id']}: {e}")

            historial.append({
                'id': fila['id'],
                'username': fila['usuario'],
                'msg': fila['mensaje'],
                'hora': hora,
                'reacciones': reacciones
            })
    except Exception as e:
        print(f"Error historial: {e}")
    finally:
        conn.close()
    
    return historial[::-1] # Retornar del más antiguo al más nuevo

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