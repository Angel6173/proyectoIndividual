from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from database import get_db_connection
from auth import auth_bp
from api.tasks import tasks_bp
from api.categories import categories_bp
from api.users import users_bp
import os
from flask import session, redirect, url_for, request
from flask import Flask
import os

# Ruta absoluta a las carpetas templates y static (fuera de backend)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)  # Sube un nivel para llegar a la raíz

app = Flask(
    __name__,
    template_folder=os.path.join(PARENT_DIR, 'templates'),
    static_folder=os.path.join(PARENT_DIR, 'static')
)
CORS(app)

app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(tasks_bp, url_prefix='/api')
app.register_blueprint(categories_bp, url_prefix='/api')
app.register_blueprint(users_bp, url_prefix='/api')

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

@app.route('/admin')
def admin_login_page():
    return render_template('admin.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    password = data.get('password')
    correct_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    if password == correct_pass:
        session['admin_logged'] = True
        return jsonify({'message': 'Acceso admin concedido'})
    
    return jsonify({'error': 'Contraseña incorrecta'}), 401

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return jsonify({'message': 'Sesión admin cerrada'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
