from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import hashlib
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
SECRET_KEY = app.secret_key

# ========== BASE DE DATOS (SQLite local / PostgreSQL en Render) ==========
def get_db():
    if 'DATABASE_URL' in os.environ:
        # Producción: PostgreSQL en Render
        import psycopg2
        from psycopg2.extras import DictCursor
        conn = psycopg2.connect(
            os.environ['DATABASE_URL'],
            cursor_factory=DictCursor,
            sslmode='require'
        )
    else:
        # Local: SQLite
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), 'taskflow.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    is_postgres = 'DATABASE_URL' in os.environ
    print("Inicializando base de datos...")
    
    # Tabla usuarios
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla tareas
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tareas (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            categoria TEXT,
            prioridad TEXT CHECK(prioridad IN ('baja', 'media', 'alta')) DEFAULT 'media',
            fecha_limite DATE,
            completada BOOLEAN DEFAULT FALSE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla categorías
    cur.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            color TEXT DEFAULT '#4361ee',
            user_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    ''')
    
    # Admin por defecto
    admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    if is_postgres:
        cur.execute('''
            INSERT INTO usuarios (nombre, email, password_hash, is_admin)
            VALUES ('Administrador', 'admin@taskflow.com', %s, TRUE)
            ON CONFLICT (email) DO NOTHING
        ''', (admin_hash,))
    else:
        cur.execute('''
            INSERT OR IGNORE INTO usuarios (nombre, email, password_hash, is_admin)
            VALUES ('Administrador', 'admin@taskflow.com', ?, 1)
        ''', (admin_hash,))
    
    conn.commit()
    cur.close()
    conn.close()
    print("Base de datos inicializada")

# ========== AYUDANTES ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_token():
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return None
    try:
        token = auth.split(' ')[1]
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except:
        return None

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = verify_token()
        if not user:
            return jsonify({'error': 'No autorizado'}), 401
        return f(user, *args, **kwargs)
    return wrapper

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = verify_token()
        if not user:
            return jsonify({'error': 'No autorizado'}), 401
        
        conn = get_db()
        cur = conn.cursor()
        placeholder = '%s' if 'DATABASE_URL' in os.environ else '?'
        cur.execute(f"SELECT is_admin FROM usuarios WHERE id = {placeholder}", (user['user_id'],))
        row = cur.fetchone()
        conn.close()
        
        if not row or not row['is_admin']:
            return jsonify({'error': 'Acceso denegado'}), 403
        
        return f(user, *args, **kwargs)
    return wrapper

# ========== AUTENTICACIÓN ==========
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Campos requeridos'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if 'DATABASE_URL' in os.environ else '?'
    cur.execute(f"SELECT * FROM usuarios WHERE email = {placeholder}", (email,))
    user = cur.fetchone()
    conn.close()
    
    if user and hash_password(password) == user['password_hash']:
        token = jwt.encode({'user_id': user['id'], 'exp': datetime.utcnow() + timedelta(days=7)}, SECRET_KEY, algorithm='HS256')
        
        redirect_to = '/admin' if user['is_admin'] else '/tasks'
        
        return jsonify({
            'token': token,
            'user': {'id': user['id'], 'nombre': user['nombre'], 'email': user['email'], 'is_admin': bool(user['is_admin'])},
            'redirect': redirect_to
        })
    
    return jsonify({'error': 'Credenciales incorrectas'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    nombre, email, password = data.get('nombre'), data.get('email'), data.get('password')
    
    if not all([nombre, email, password]) or len(password) < 6:
        return jsonify({'error': 'Datos inválidos'}), 400
    
    hashed = hash_password(password)
    
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if 'DATABASE_URL' in os.environ else '?'
    try:
        cur.execute(f"INSERT INTO usuarios (nombre, email, password_hash) VALUES ({placeholder}, {placeholder}, {placeholder})", (nombre, email, hashed))
        conn.commit()
        return jsonify({'message': 'Registrado'}), 201
    except Exception as e:
        return jsonify({'error': 'Email ya existe'}), 400
    finally:
        conn.close()

# ========== TAREAS ==========
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    user = verify_token()
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if 'DATABASE_URL' in os.environ else '?'
    
    if user:
        cur.execute(f"SELECT * FROM tareas WHERE user_id = {placeholder} ORDER BY fecha_limite ASC, prioridad DESC", (user['user_id'],))
    else:
        cur.execute("SELECT * FROM tareas WHERE 1=0")
    
    tasks = cur.fetchall()
    conn.close()
    return jsonify([dict(t) for t in tasks])

@app.route('/api/tasks', methods=['POST'])
@require_auth
def create_task(user):
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if 'DATABASE_URL' in os.environ else '?'
    
    cur.execute(f"""
        INSERT INTO tareas (titulo, descripcion, categoria, prioridad, fecha_limite, user_id)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (
        data['titulo'],
        data.get('descripcion'),
        data.get('categoria'),
        data.get('prioridad', 'media'),
        data.get('fecha_limite'),
        user['user_id']
    ))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Tarea creada'}), 201

@app.route('/api/tasks/<int:id>', methods=['PUT'])
@require_auth
def update_task(user, id):
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if 'DATABASE_URL' in os.environ else '?'
    
    cur.execute(f"UPDATE tareas SET completada = {placeholder} WHERE id = {placeholder} AND user_id = {placeholder}", 
                (data.get('completada'), id, user['user_id']))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Tarea actualizada'})

@app.route('/api/tasks/<int:id>', methods=['DELETE'])
@require_auth
def delete_task(user, id):
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if 'DATABASE_URL' in os.environ else '?'
    
    cur.execute(f"DELETE FROM tareas WHERE id = {placeholder} AND user_id = {placeholder}", (id, user['user_id']))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Tarea eliminada'})

# ========== CALENDARIO ==========
@app.route('/api/calendar/tasks', methods=['GET'])
def get_calendar_tasks():
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if 'DATABASE_URL' in os.environ else '?'
    
    auth_header = request.headers.get('Authorization')
    user_id = None
    
    if auth_header and auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except:
            pass
    
    if not user_id:
        conn.close()
        return jsonify([])
    
    cur.execute(f"""
        SELECT id, titulo, descripcion, categoria, prioridad, completada, fecha_limite
        FROM tareas 
        WHERE user_id = {placeholder} AND fecha_limite IS NOT NULL
        ORDER BY fecha_limite ASC
    """, (user_id,))
    
    tasks = cur.fetchall()
    conn.close()
    
    events = []
    for task in tasks:
        if task['prioridad'] == 'alta':
            bg = '#f56565'; border = '#c53030'; text = '#fff'
        elif task['prioridad'] == 'media':
            bg = '#fbbf24'; border = '#f59e0b'; text = '#1f2937'
        else:
            bg = '#48bb78'; border = '#38a169'; text = '#fff'
        
        if task['completada']:
            bg = '#a0aec0'; border = '#718096'; text = '#4a5568'
            title = f"{task['titulo']} (✓ Completada)"
        else:
            title = task['titulo']
        
        events.append({
            'id': task['id'],
            'title': title,
            'start': task['fecha_limite'],
            'allDay': True,
            'backgroundColor': bg,
            'borderColor': border,
            'textColor': text,
            'description': task['descripcion'] or '',
            'extendedProps': {
                'categoria': task['categoria'] or 'Sin categoría',
                'prioridad': task['prioridad'].capitalize(),
            }
        })
    
    return jsonify(events)

# ========== RUTAS DE ADMIN ==========
@app.route('/api/admin/stats')
@require_admin
def admin_stats(user):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM usuarios")
    total_users = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM tareas")
    total_tasks = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM categorias")
    total_categories = cur.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_users': total_users,
        'total_tasks': total_tasks,
        'total_categories': total_categories
    })

@app.route('/api/admin/users')
@require_admin
def admin_users(user):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, email, fecha_registro, is_admin FROM usuarios ORDER BY fecha_registro DESC")
    users = cur.fetchall()
    conn.close()
    
    user_list = [dict(u) for u in users]
    for u in user_list:
        u['is_admin'] = bool(u['is_admin'])
    
    return jsonify(user_list)

# ========== RUTAS HTML ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/tasks')
def tasks_page():
    return render_template('tasks.html')

@app.route('/calendar')
def calendar_page():
    return render_template('calendar.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# ========== INICIALIZACIÓN ==========
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)