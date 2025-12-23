from flask import Blueprint, jsonify, session
from database import get_db_connection

admin_api_bp = Blueprint('admin_api', __name__)

def require_admin():
    if not session.get('admin_logged'):
        return jsonify({'error': 'Acceso denegado'}), 401
    return None

@admin_api_bp.route('/users')
def admin_users():
    auth_check = require_admin()
    if auth_check: return auth_check
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, email, fecha_registro FROM usuarios WHERE is_admin = FALSE")
    users = cursor.fetchall()
    conn.close()
    return jsonify(users)

@admin_api_bp.route('/all-tasks')
def admin_all_tasks():
    auth_check = require_admin()
    if auth_check: return auth_check
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.*, u.nombre as usuario_nombre, u.email as usuario_email 
        FROM tareas t 
        JOIN usuarios u ON t.user_id = u.id 
        ORDER BY t.fecha_creacion DESC
    """)
    tasks = cursor.fetchall()
    conn.close()
    return jsonify(tasks)

@admin_api_bp.route('/stats')
def admin_stats():
    auth_check = require_admin()
    if auth_check: return auth_check
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE is_admin = FALSE")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tareas")
    total_tasks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM categorias")
    total_categories = cursor.fetchone()[0]
    
    conn.close()
    return jsonify({
        'total_users': total_users,
        'total_tasks': total_tasks,
        'total_categories': total_categories
    })