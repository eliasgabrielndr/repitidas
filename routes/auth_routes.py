from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
import json
import os
import uuid
from datetime import datetime
import hashlib
from functools import wraps
from src.models.user import User

auth_bp = Blueprint('auth', __name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users.json')

# Garantir que o diretório de dados exista
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# Garantir que o arquivo de usuários exista
if not os.path.exists(DATA_FILE):
    # Criar o arquivo com o usuário administrador padrão
    admin_user = User(
        username="eliasndr",
        password=hashlib.sha256("1408Masp@".encode()).hexdigest(),
        is_admin=True,
        post_limit=None  # Sem limite para o administrador
    )
    with open(DATA_FILE, 'w') as f:
        json.dump([admin_user.to_dict()], f, indent=2)
    print(f"Arquivo de usuários criado com administrador padrão: {DATA_FILE}")

def load_users():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return [User.from_dict(user_data) for user_data in data]
    except Exception as e:
        print(f"Erro ao carregar usuários: {e}")
        # Se houver erro, retorna lista vazia e recria o arquivo com admin padrão
        admin_user = User(
            username="eliasndr",
            password=hashlib.sha256("1408Masp@".encode()).hexdigest(),
            is_admin=True,
            post_limit=None
        )
        with open(DATA_FILE, 'w') as f:
            json.dump([admin_user.to_dict()], f, indent=2)
        return [admin_user]

def save_users(users):
    try:
        # Garantir que o diretório exista antes de salvar
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        with open(DATA_FILE, 'w') as f:
            json.dump([user.to_dict() for user in users], f, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar usuários: {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        
        users = load_users()
        user = next((u for u in users if u.id == session['user_id']), None)
        
        if not user or not user.is_admin:
            flash('Acesso negado. Você precisa ser administrador para acessar esta página.', 'danger')
            return redirect(url_for('posts.index'))
        
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, preencha todos os campos.', 'danger')
            return render_template('auth/login.html')
        
        # Hash da senha para comparação
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        users = load_users()
        user = next((u for u in users if u.username == username and u.password == password_hash), None)
        
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('posts.index'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/users')
@admin_required
def list_users():
    users = load_users()
    return render_template('auth/users.html', users=users)

@auth_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form
        post_limit = request.form.get('post_limit')
        
        if not username or not password:
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return render_template('auth/create_user.html')
        
        # Verificar se o usuário já existe
        users = load_users()
        if any(u.username == username for u in users):
            flash('Este nome de usuário já está em uso.', 'danger')
            return render_template('auth/create_user.html')
        
        # Converter post_limit para inteiro ou None
        if post_limit and post_limit.isdigit():
            post_limit = int(post_limit)
        else:
            post_limit = None
        
        # Hash da senha
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Criar novo usuário
        new_user = User(
            username=username,
            password=password_hash,
            is_admin=is_admin,
            post_limit=post_limit
        )
        
        users.append(new_user)
        save_users(users)
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('auth.list_users'))
    
    return render_template('auth/create_user.html')

@auth_bp.route('/users/<user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    users = load_users()
    user = next((u for u in users if u.id == user_id), None)
    
    if not user:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('auth.list_users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form
        post_limit = request.form.get('post_limit')
        
        if not username:
            flash('Por favor, preencha o nome de usuário.', 'danger')
            return render_template('auth/edit_user.html', user=user)
        
        # Verificar se o novo nome de usuário já existe (se foi alterado)
        if username != user.username and any(u.username == username for u in users):
            flash('Este nome de usuário já está em uso.', 'danger')
            return render_template('auth/edit_user.html', user=user)
        
        # Atualizar usuário
        for i, u in enumerate(users):
            if u.id == user_id:
                users[i].username = username
                
                # Atualizar senha apenas se fornecida
                if password:
                    users[i].password = hashlib.sha256(password.encode()).hexdigest()
                
                users[i].is_admin = is_admin
                
                # Converter post_limit para inteiro ou None
                if post_limit and post_limit.isdigit():
                    users[i].post_limit = int(post_limit)
                else:
                    users[i].post_limit = None
                
                users[i].updated_at = datetime.now()
                break
        
        save_users(users)
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('auth.list_users'))
    
    return render_template('auth/edit_user.html', user=user)

@auth_bp.route('/users/<user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    # Não permitir excluir o próprio usuário
    if session.get('user_id') == user_id:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('auth.list_users'))
    
    users = load_users()
    users = [u for u in users if u.id != user_id]
    save_users(users)
    
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('auth.list_users'))
