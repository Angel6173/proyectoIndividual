from flask import Blueprint, request, jsonify
import jwt
from datetime import datetime, timedelta
from .database import get_db_connection
import hashlib

auth_bp = Blueprint('auth', __name__)
SECRET_KEY = 'cambia_esta_clave_secreta_por_una_muy_larga'

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user and hash_password(password) == user['password_hash']:
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.utcnow() + timedelta(days=7)
        }, SECRET_KEY, algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': {'id': user['id'], 'nombre': user['nombre'], 'email': user['email']}
        })
    
    return jsonify({'error': 'Credenciales incorrectas'}), 401

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    nombre = data.get('nombre')
    email = data.get('email')
    password = data.get('password')
    
    hashed = hash_password(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO usuarios (nombre, email, password_hash)
            VALUES (%s, %s, %s)
        """, (nombre, email, hashed))
        conn.commit()
        user_id = cursor.lastrowid
        return jsonify({'message': 'Cuenta creada', 'user_id': user_id}), 201
    except mysql.connector.errors.IntegrityError:
        return jsonify({'error': 'El email ya está registrado'}), 400
    finally:
        conn.close()

def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except:
        return None