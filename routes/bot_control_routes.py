from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import os
from src.telegram_bot_service import TelegramBotService
from src.routes.bot_routes import load_bots

bot_control_bp = Blueprint('bot_control', __name__, url_prefix='/bot')

# Inicializar o serviço do bot
data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
bot_service = TelegramBotService(data_dir)

@bot_control_bp.route('/start/<bot_id>', methods=['POST'])
def start_bot(bot_id):
    """Inicia um bot específico"""
    success = bot_service.start_bot(bot_id)
    return jsonify({"success": success, "status": bot_service.status()})

@bot_control_bp.route('/stop/<bot_id>', methods=['POST'])
def stop_bot(bot_id):
    """Para um bot específico"""
    success = bot_service.stop_bot(bot_id)
    return jsonify({"success": success, "status": bot_service.status()})

@bot_control_bp.route('/start_all', methods=['POST'])
def start_all_bots():
    """Inicia todos os bots cadastrados"""
    success_count = bot_service.start_all_bots()
    return jsonify({
        "success": success_count > 0, 
        "message": f"{success_count} bots iniciados com sucesso",
        "status": bot_service.status()
    })

@bot_control_bp.route('/stop_all', methods=['POST'])
def stop_all_bots():
    """Para todos os bots em execução"""
    success_count = bot_service.stop_all_bots()
    return jsonify({
        "success": True, 
        "message": f"{success_count} bots parados com sucesso",
        "status": bot_service.status()
    })

@bot_control_bp.route('/status', methods=['GET'])
def bot_status():
    """Retorna o status atual dos bots"""
    return jsonify(bot_service.status())
