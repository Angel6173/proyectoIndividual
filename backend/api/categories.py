from flask import Blueprint, request, jsonify
from ..database import get_db_connection
from auth import verify_token

categories_bp = Blueprint('categories', __name__)

@categories_bp.route('/categories', methods=['GET', 'POST'])
def categories():
    user = verify_token()
    if not user:
        return jsonify({'error': 'No autorizado'}), 401
    user_id = user['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        data = request.json
        cursor.execute("""
            INSERT INTO categorias (nombre, color, user_id)
            VALUES (%s, %s, %s)
        """, (data['nombre'], data.get('color', '#4361ee'), user_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Categoría creada'})
    
    cursor.execute("SELECT * FROM categorias WHERE user_id = %s", (user_id,))
    cats = cursor.fetchall()
    conn.close()
    return jsonify(cats)