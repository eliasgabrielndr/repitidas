import os
import uuid
from werkzeug.utils import secure_filename

# Configurações para upload de arquivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'webm'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

# Garantir que o diretório de uploads exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Verifica se o arquivo tem uma extensão permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determina o tipo de arquivo com base na extensão"""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        return 'photo'
    elif ext in {'mp4', 'avi', 'mov', 'webm'}:
        return 'video'
    return None

def save_uploaded_file(file):
    """Salva um arquivo enviado e retorna o caminho relativo"""
    if file and allowed_file(file.filename):
        # Gerar um nome de arquivo seguro e único
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Caminho completo para salvar o arquivo
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Salvar o arquivo
        file.save(file_path)
        
        # Retornar o caminho relativo para armazenar no banco de dados
        relative_path = os.path.join('static', 'uploads', unique_filename)
        
        return {
            'success': True,
            'file_path': relative_path,
            'file_type': get_file_type(filename),
            'original_name': filename
        }
    
    return {
        'success': False,
        'error': 'Tipo de arquivo não permitido'
    }

def delete_file(file_path):
    """Deleta um arquivo do sistema de arquivos"""
    try:
        # Verificar se o caminho é relativo e convertê-lo para absoluto
        if not os.path.isabs(file_path):
            absolute_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
        else:
            absolute_path = file_path
        
        # Verificar se o arquivo existe
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
            return True
        return False
    except Exception as e:
        print(f"Erro ao deletar arquivo: {e}")
        return False

def get_media_list():
    """Retorna uma lista de todos os arquivos de mídia disponíveis"""
    try:
        files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join('static', 'uploads', filename)
            file_type = get_file_type(filename) if '.' in filename else None
            
            if file_type:
                files.append({
                    'name': filename,
                    'path': file_path,
                    'type': file_type,
                    'size': os.path.getsize(os.path.join(UPLOAD_FOLDER, filename)) // 1024  # tamanho em KB
                })
        
        # Ordenar por data de modificação (mais recentes primeiro)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x['name'])), reverse=True)
        
        return files
    except Exception as e:
        print(f"Erro ao listar arquivos de mídia: {e}")
        return []
