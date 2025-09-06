# app.py (Versão com Emojis e Upload de Fotos)
import sqlite3
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
import os
import uuid # Para gerar nomes de arquivo únicos
from werkzeug.utils import secure_filename

# --- CONFIGURAÇÃO INICIAL E DE UPLOAD ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-dificil-de-adivinhar!'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app)

# Garante que a pasta de uploads exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

active_users = set()

# --- FUNÇÕES DE BANCO DE DADOS (sem alteração) ---
def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    return conn
# ... (create_tables, get_all_usernames, hash_password permanecem iguais)
DATABASE_NAME = 'chat.db'
def create_tables():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)')
    conn.commit()
    conn.close()
def get_all_usernames():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users ORDER BY username")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- ROTAS HTTP ---
# Rotas de login, register, /, logout continuam as mesmas.
# Adicionaremos duas novas rotas para os arquivos.

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()
        if user_data and user_data[0] == hash_password(password):
            session['username'] = username
            return redirect(url_for('chat'))
        else:
            error = "Usuário ou senha inválidos."
    return render_template('login.html', error=error)

@app.route('/register', methods=['POST'])
def register():
    username, password = request.form['username'], request.form['password']
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
    except sqlite3.IntegrityError:
        return render_template('login.html', error="Usuário já existe.")
    finally:
        conn.close()
    return redirect(url_for('login'))

@app.route('/')
def chat():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('chat.html', username=session['username'])

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# NOVA ROTA: Para servir os arquivos da pasta 'uploads' de forma segura
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Função auxiliar para verificar a extensão do arquivo
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# NOVA ROTA: Para receber o upload das fotos
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    if 'photo' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['photo']
    
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
    if file and allowed_file(file.filename):
        # Cria um nome de arquivo seguro e único
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Notifica a sala de chat sobre a nova imagem
        username = session['username']
        room = 'geral' # Assumindo uma sala única por enquanto
        image_url = url_for('uploaded_file', filename=filename)
        
        socketio.emit('receive_message', {
            'user': username, 
            'type': 'image', # Novo tipo de mensagem
            'url': image_url
        }, to=room)
        
        return jsonify({'success': 'Arquivo enviado'}), 200
    
    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400

# --- LÓGICA DO SOCKET.IO ---
# (Pequena alteração em 'send_message' para adicionar o tipo 'text')
def broadcast_user_list():
    all_users = get_all_usernames()
    user_list_with_status = [{'name': user, 'status': 'active' if user in active_users else 'inactive'} for user in all_users]
    socketio.emit('update_user_list', user_list_with_status)

@socketio.on('connect')
def on_connect():
    if 'username' in session:
        username = session['username']
        active_users.add(username)
        broadcast_user_list()

@socketio.on('join')
def on_join(data):
    username = session['username']
    room = data['room']
    join_room(room)
    emit('status', {'msg': f'{username} entrou na sala.'}, to=room)

@socketio.on('send_message')
def on_send_message(data):
    username = session['username']
    room = data['room']
    # Adicionamos um 'type' para diferenciar texto de imagem
    message_data = {'user': username, 'type': 'text', 'msg': data['msg']}
    emit('receive_message', message_data, to=room)

@socketio.on('disconnect')
def on_disconnect():
    if 'username' in session:
        username = session['username']
        active_users.discard(username)
        broadcast_user_list()

# --- INICIALIZAÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    create_tables()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)