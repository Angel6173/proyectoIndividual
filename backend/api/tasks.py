from flask import Blueprint, request, jsonify
from ..database import get_db_connection
from auth import verify_token

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/tasks', methods=['GET', 'POST'])
def tasks():
    user = verify_token()
    if not user:
        return jsonify({'error': 'No autorizado'}), 401
    user_id = user['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        data = request.json
        cursor.execute("""
            INSERT INTO tareas (titulo, descripcion, categoria, prioridad, fecha_limite, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data['titulo'], data.get('descripcion'), data.get('categoria'), 
              data.get('prioridad', 'media'), data.get('fecha_limite'), user_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Tarea creada'})
    
    cursor.execute("SELECT * FROM tareas WHERE user_id = %s ORDER BY fecha_creacion DESC", (user_id,))
    tasks_list = cursor.fetchall()
    conn.close()
    return jsonify(tasks_list)

@tasks_bp.route('/tasks/<int:id>', methods=['PUT', 'DELETE'])
def task_detail(id):
    user = verify_token()
    if not user:
        return jsonify({'error': 'No autorizado'}), 401
    user_id = user['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'DELETE':
        cursor.execute("DELETE FROM tareas WHERE id = %s AND user_id = %s", (id, user_id))
    elif request.method == 'PUT':
        data = request.json
        if 'completada' in data:
            cursor.execute("UPDATE tareas SET completada = %s WHERE id = %s AND user_id = %s",
                           (data['completada'], id, user_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'OK'})