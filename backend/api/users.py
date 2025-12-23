from flask import Blueprint, jsonify
from auth import verify_token

users_bp = Blueprint('users', __name__)

@users_bp.route('/me')
def me():
    user = verify_token()
    if not user:
        return jsonify({'error': 'No autorizado'}), 401
    return jsonify({'user_id': user['user_id']})