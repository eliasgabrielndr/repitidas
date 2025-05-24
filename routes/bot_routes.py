from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import json
import os
import uuid
from datetime import datetime
from src.models.bot import Bot

bot_bp = Blueprint('bots', __name__, url_prefix='/bots')

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'bots.json')

# Garantir que o diretório de dados exista
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# Garantir que o arquivo de bots exista
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

def load_bots():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return [Bot.from_dict(bot_data) for bot_data in data]
    except Exception as e:
        print(f"Erro ao carregar bots: {e}")
        # Se houver erro, retorna lista vazia e recria o arquivo
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)
        return []

def save_bots(bots):
    try:
        # Garantir que o diretório exista antes de salvar
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        with open(DATA_FILE, 'w') as f:
            json.dump([bot.to_dict() for bot in bots], f, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar bots: {e}")
        return False

@bot_bp.route('/')
def index():
    bots = load_bots()
    return render_template('bots/index.html', bots=bots)

@bot_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        data = request.form.to_dict()
        
        # Processar grupos como lista
        default_groups = [group.strip() for group in data.get('default_groups', '').split(',') if group.strip()]
        
        bot = Bot(
            id=str(uuid.uuid4()),
            name=data.get('name'),
            token=data.get('token'),
            default_groups=default_groups,
            is_active=False
        )
        
        bots = load_bots()
        bots.append(bot)
        save_bots(bots)
        
        return redirect(url_for('bots.index'))
    
    return render_template('bots/create.html')

@bot_bp.route('/<bot_id>', methods=['GET'])
def view(bot_id):
    bots = load_bots()
    bot = next((b for b in bots if b.id == bot_id), None)
    
    if not bot:
        return redirect(url_for('bots.index'))
    
    return render_template('bots/view.html', bot=bot)

@bot_bp.route('/<bot_id>/edit', methods=['GET', 'POST'])
def edit(bot_id):
    bots = load_bots()
    bot = next((b for b in bots if b.id == bot_id), None)
    
    if not bot:
        return redirect(url_for('bots.index'))
    
    if request.method == 'POST':
        data = request.form.to_dict()
        
        # Processar grupos como lista
        default_groups = [group.strip() for group in data.get('default_groups', '').split(',') if group.strip()]
        
        for i, b in enumerate(bots):
            if b.id == bot_id:
                bots[i].name = data.get('name')
                bots[i].token = data.get('token')
                bots[i].default_groups = default_groups
                bots[i].updated_at = datetime.now()
                break
        
        save_bots(bots)
        return redirect(url_for('bots.index'))
    
    return render_template('bots/edit.html', bot=bot)

@bot_bp.route('/<bot_id>/delete', methods=['POST'])
def delete(bot_id):
    bots = load_bots()
    bots = [b for b in bots if b.id != bot_id]
    save_bots(bots)
    return redirect(url_for('bots.index'))

@bot_bp.route('/<bot_id>/toggle_status', methods=['POST'])
def toggle_status(bot_id):
    bots = load_bots()
    
    for i, bot in enumerate(bots):
        if bot.id == bot_id:
            bots[i].is_active = not bots[i].is_active
            bots[i].updated_at = datetime.now()
            break
    
    save_bots(bots)
    return redirect(url_for('bots.index'))

@bot_bp.route('/api/list', methods=['GET'])
def api_list():
    bots = load_bots()
    return jsonify([bot.to_dict() for bot in bots])
