import sys
import os
import json

# Função para inicializar todos os arquivos e diretórios necessários
def initialize_data_files():
    # Definir caminhos para diretórios e arquivos
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    bots_file = os.path.join(data_dir, 'bots.json')
    posts_file = os.path.join(data_dir, 'posts.json')
    
    # Garantir que o diretório de dados exista
    os.makedirs(data_dir, exist_ok=True)
    
    # Inicializar arquivo de bots se não existir
    if not os.path.exists(bots_file):
        with open(bots_file, 'w') as f:
            json.dump([], f)
        print(f"Arquivo de bots criado: {bots_file}")
    
    # Inicializar arquivo de posts se não existir
    if not os.path.exists(posts_file):
        with open(posts_file, 'w') as f:
            json.dump([], f)
        print(f"Arquivo de posts criado: {posts_file}")
    
    return data_dir

# Adicionar o diretório pai ao path para permitir importações absolutas
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Inicializar arquivos e diretórios antes de importar outros módulos
data_dir = initialize_data_files()

from flask import Flask, render_template, redirect, url_for
# Importações absolutas que funcionam tanto em execução direta quanto como módulo
from src.routes.post_routes import post_bp
from src.routes.bot_routes import bot_bp, load_bots
from src.routes.bot_control_routes import bot_control_bp
from src.routes.auth_routes import auth_bp
from src.telegram_bot_service import TelegramBotService

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Registrar blueprints
app.register_blueprint(post_bp)
app.register_blueprint(bot_bp)
app.register_blueprint(bot_control_bp)
app.register_blueprint(auth_bp)

# Adicionar função auxiliar para templates
@app.context_processor
def utility_processor():
    def get_bot_name(bot_id):
        if not bot_id:
            return None
        bots = load_bots()
        bot = next((b for b in bots if b.id == bot_id), None)
        return bot.name if bot else None
    
    return dict(get_bot_name=get_bot_name)

# Rota principal
@app.route('/')
def index():
    return redirect(url_for('posts.index'))

if __name__ == '__main__':
    # Inicializar o serviço do bot
    bot_service = TelegramBotService(data_dir)
    
    # Imprimir informações de inicialização
    print(f"Diretório de dados: {data_dir}")
    print(f"Arquivos inicializados com sucesso")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
