from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
import json
import os
import uuid
from datetime import datetime
from src.models.post import Post
from src.routes.bot_routes import load_bots
from src.routes.auth_routes import login_required
from src.utils.file_upload import save_uploaded_file, delete_file, get_media_list

post_bp = Blueprint('posts', __name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'posts.json')

# Garantir que o diretório de dados exista
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# Garantir que o arquivo de posts exista
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

def load_posts():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return [Post.from_dict(post_data) for post_data in data]
    except Exception as e:
        print(f"Erro ao carregar posts: {e}")
        # Se houver erro, retorna lista vazia e recria o arquivo
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)
        return []

def save_posts(posts):
    try:
        # Garantir que o diretório exista antes de salvar
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        with open(DATA_FILE, 'w') as f:
            json.dump([post.to_dict() for post in posts], f, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar posts: {e}")
        return False

@post_bp.route('/')
@login_required
def index():
    posts = load_posts()
    bots = load_bots()
    
    # Filtrar posts pelo usuário atual, exceto para admin
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    # Obter informações sobre o limite de publicações do usuário
    user_post_limit = None
    user_post_count = 0
    
    if not is_admin:
        posts = [post for post in posts if post.user_id == user_id]
        
        # Obter limite de publicações do usuário
        from src.routes.auth_routes import load_users
        users = load_users()
        user = next((u for u in users if u.id == user_id), None)
        
        if user:
            user_post_limit = user.post_limit
            user_post_count = len(posts)
    
    return render_template('index.html', posts=posts, bots=bots, 
                          user_post_limit=user_post_limit, 
                          user_post_count=user_post_count)

@post_bp.route('/posts', methods=['GET'])
@login_required
def get_posts():
    posts = load_posts()
    
    # Filtrar posts pelo usuário atual, exceto para admin
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not is_admin:
        posts = [post for post in posts if post.user_id == user_id]
    
    return jsonify([post.to_dict() for post in posts])

@post_bp.route('/posts', methods=['POST'])
@login_required
def create_post():
    # Verificar limite de publicações do usuário
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not is_admin:
        from src.routes.auth_routes import load_users
        users = load_users()
        user = next((u for u in users if u.id == user_id), None)
        
        if user and user.post_limit is not None:
            # Contar publicações do usuário
            posts = load_posts()
            user_posts_count = sum(1 for post in posts if post.user_id == user_id)
            
            if user_posts_count >= user.post_limit:
                flash('Você atingiu o limite de publicações permitido.', 'danger')
                return redirect(url_for('posts.index'))
    
    data = request.form.to_dict()
    
    # Processar grupos como lista
    groups = [group.strip() for group in data.get('groups', '').split(',') if group.strip()]
    
    # Verificar se há auto_delete
    auto_delete = 'auto_delete' in request.form
    
    # Processar upload de arquivo se houver
    file = request.files.get('media_file')
    media_type = data.get('media_type')
    media_url = data.get('media_url')
    
    if file and file.filename:
        upload_result = save_uploaded_file(file)
        if upload_result['success']:
            media_url = upload_result['file_path']
            media_type = upload_result['file_type']
        else:
            flash(f"Erro ao fazer upload do arquivo: {upload_result.get('error')}", 'danger')
            return redirect(url_for('posts.index'))
    
    post = Post(
        id=str(uuid.uuid4()),
        bot_id=data.get('bot_id'),
        media_type=media_type,
        media_url=media_url,
        caption=data.get('caption'),
        button_text=data.get('button_text'),
        button_url=data.get('button_url'),
        interval_seconds=int(data.get('interval_seconds', 0)),
        groups=groups,
        user_id=user_id,
        auto_delete=auto_delete
    )
    
    posts = load_posts()
    posts.append(post)
    save_posts(posts)
    
    flash('Publicação criada com sucesso!', 'success')
    return redirect(url_for('posts.index'))

@post_bp.route('/posts/<post_id>', methods=['GET'])
@login_required
def get_post(post_id):
    posts = load_posts()
    post = next((p for p in posts if p.id == post_id), None)
    
    if not post:
        flash('Publicação não encontrada.', 'danger')
        return redirect(url_for('posts.index'))
    
    # Verificar permissão (apenas admin ou dono da publicação)
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not is_admin and post.user_id != user_id:
        flash('Você não tem permissão para visualizar esta publicação.', 'danger')
        return redirect(url_for('posts.index'))
    
    if post:
        return jsonify(post.to_dict())
    return jsonify({"error": "Post não encontrado"}), 404

@post_bp.route('/posts/<post_id>', methods=['POST'])
@login_required
def update_post(post_id):
    posts = load_posts()
    post = next((p for p in posts if p.id == post_id), None)
    
    if not post:
        flash('Publicação não encontrada.', 'danger')
        return redirect(url_for('posts.index'))
    
    # Verificar permissão (apenas admin ou dono da publicação)
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not is_admin and post.user_id != user_id:
        flash('Você não tem permissão para editar esta publicação.', 'danger')
        return redirect(url_for('posts.index'))
    
    data = request.form.to_dict()
    
    for i, p in enumerate(posts):
        if p.id == post_id:
            # Processar grupos como lista
            groups = [group.strip() for group in data.get('groups', '').split(',') if group.strip()]
            
            # Verificar se há auto_delete
            auto_delete = 'auto_delete' in request.form
            
            # Processar upload de arquivo se houver
            file = request.files.get('media_file')
            media_type = data.get('media_type')
            media_url = data.get('media_url')
            
            if file and file.filename:
                upload_result = save_uploaded_file(file)
                if upload_result['success']:
                    # Se havia um arquivo anterior, excluí-lo
                    if p.media_url and os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), p.media_url)):
                        delete_file(p.media_url)
                    
                    media_url = upload_result['file_path']
                    media_type = upload_result['file_type']
                else:
                    flash(f"Erro ao fazer upload do arquivo: {upload_result.get('error')}", 'danger')
                    return redirect(url_for('posts.index'))
            
            posts[i].bot_id = data.get('bot_id')
            posts[i].media_type = media_type
            posts[i].media_url = media_url
            posts[i].caption = data.get('caption')
            posts[i].button_text = data.get('button_text')
            posts[i].button_url = data.get('button_url')
            posts[i].interval_seconds = int(data.get('interval_seconds', 0))
            posts[i].groups = groups
            posts[i].updated_at = datetime.now()
            posts[i].auto_delete = auto_delete
            
            save_posts(posts)
            flash('Publicação atualizada com sucesso!', 'success')
            return redirect(url_for('posts.index'))
    
    flash('Erro ao atualizar publicação.', 'danger')
    return redirect(url_for('posts.index'))

@post_bp.route('/posts/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    posts = load_posts()
    post = next((p for p in posts if p.id == post_id), None)
    
    if not post:
        flash('Publicação não encontrada.', 'danger')
        return redirect(url_for('posts.index'))
    
    # Verificar permissão (apenas admin ou dono da publicação)
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not is_admin and post.user_id != user_id:
        flash('Você não tem permissão para excluir esta publicação.', 'danger')
        return redirect(url_for('posts.index'))
    
    # Excluir arquivo de mídia se for local
    if post.media_url and not post.media_url.startswith(('http://', 'https://')):
        delete_file(post.media_url)
    
    posts = [p for p in posts if p.id != post_id]
    save_posts(posts)
    
    flash('Publicação excluída com sucesso!', 'success')
    return redirect(url_for('posts.index'))

@post_bp.route('/posts/<post_id>/toggle-auto-delete', methods=['POST'])
@login_required
def toggle_auto_delete(post_id):
    """Ativa/desativa a deleção automática para uma publicação"""
    posts = load_posts()
    post = next((p for p in posts if p.id == post_id), None)
    
    if not post:
        return jsonify({'success': False, 'message': 'Publicação não encontrada'})
    
    # Verificar permissão (apenas admin ou dono da publicação)
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not is_admin and post.user_id != user_id:
        return jsonify({'success': False, 'message': 'Permissão negada'})
    
    # Alternar o estado de auto_delete
    for i, p in enumerate(posts):
        if p.id == post_id:
            posts[i].auto_delete = not posts[i].auto_delete
            auto_delete = posts[i].auto_delete
            break
    
    save_posts(posts)
    
    return jsonify({
        'success': True, 
        'auto_delete': auto_delete,
        'message': f"Deleção automática {'ativada' if auto_delete else 'desativada'}"
    })

@post_bp.route('/media')
@login_required
def media_library():
    """Exibe a biblioteca de mídia"""
    media_list = get_media_list()
    return render_template('media_library.html', media_list=media_list)

@post_bp.route('/media/upload', methods=['POST'])
@login_required
def upload_media():
    """Faz upload de um arquivo para a biblioteca de mídia"""
    if 'media_file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('posts.media_library'))
    
    file = request.files['media_file']
    
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('posts.media_library'))
    
    upload_result = save_uploaded_file(file)
    
    if upload_result['success']:
        flash('Arquivo enviado com sucesso!', 'success')
    else:
        flash(f"Erro ao fazer upload do arquivo: {upload_result.get('error')}", 'danger')
    
    return redirect(url_for('posts.media_library'))

@post_bp.route('/media/delete', methods=['POST'])
@login_required
def delete_media():
    """Exclui um arquivo da biblioteca de mídia"""
    file_path = request.form.get('file_path')
    
    if not file_path:
        flash('Caminho do arquivo não fornecido.', 'danger')
        return redirect(url_for('posts.media_library'))
    
    # Verificar se o arquivo está sendo usado em alguma publicação
    posts = load_posts()
    is_used = any(post.media_url == file_path for post in posts)
    
    if is_used:
        flash('Este arquivo está sendo usado em uma ou mais publicações e não pode ser excluído.', 'danger')
        return redirect(url_for('posts.media_library'))
    
    # Excluir o arquivo
    if delete_file(file_path):
        flash('Arquivo excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir o arquivo.', 'danger')
    
    return redirect(url_for('posts.media_library'))

@post_bp.route('/posts/status', methods=['GET'])
@login_required
def get_posts_status():
    """Retorna o status atual de todas as publicações"""
    from src.main import bot_service
    
    posts = load_posts()
    bots = load_bots()
    
    # Filtrar posts pelo usuário atual, exceto para admin
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    
    if not is_admin:
        posts = [post for post in posts if post.user_id == user_id]
    
    # Mapear IDs de bots para nomes
    bot_names = {bot.id: bot.name for bot in bots}
    
    # Obter status de cada publicação
    posts_status = []
    for post in posts:
        last_sent = bot_service.last_sent.get(post.id)
        last_sent_str = datetime.fromtimestamp(last_sent).strftime('%Y-%m-%d %H:%M:%S') if last_sent else 'Nunca'
        
        posts_status.append({
            'id': post.id,
            'bot_id': post.bot_id,
            'bot_name': bot_names.get(post.bot_id, 'Bot desconhecido'),
            'active': getattr(post, 'active', True),
            'auto_delete': getattr(post, 'auto_delete', False),
            'last_sent': last_sent_str,
            'send_status': post.send_status
        })
    
    return jsonify({
        'success': True,
        'posts': posts_status,
        'bot_service_status': bot_service.status()
    })
