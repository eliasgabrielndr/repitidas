import asyncio
import json
import os
import time
import threading
from datetime import datetime
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError
from src.models.bot import Bot as BotModel
from src.models.post import Post

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramBotService:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.bots_file = os.path.join(data_dir, 'bots.json')
        self.posts_file = os.path.join(data_dir, 'posts.json')
        self.active_bots = {}  # {bot_id: Bot instance}
        self.is_running = False
        self.threads = {}  # {bot_id: thread}
        self.last_sent = {}  # {post_id: timestamp}
        
        # Garantir que os arquivos existam
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Garante que os arquivos necessários existam"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        if not os.path.exists(self.bots_file):
            with open(self.bots_file, 'w') as f:
                json.dump([], f)
            logger.info(f"Arquivo de bots criado: {self.bots_file}")
        
        if not os.path.exists(self.posts_file):
            with open(self.posts_file, 'w') as f:
                json.dump([], f)
            logger.info(f"Arquivo de posts criado: {self.posts_file}")
    
    def load_bots(self):
        """Carrega os bots cadastrados"""
        self._ensure_files_exist()
        
        try:
            with open(self.bots_file, 'r') as f:
                data = json.load(f)
                return [BotModel.from_dict(bot_data) for bot_data in data]
        except Exception as e:
            logger.error(f"Erro ao carregar bots: {e}")
            # Se houver erro, retorna lista vazia e recria o arquivo
            with open(self.bots_file, 'w') as f:
                json.dump([], f)
            return []
    
    def load_posts(self):
        """Carrega as publicações salvas"""
        self._ensure_files_exist()
        
        try:
            with open(self.posts_file, 'r') as f:
                data = json.load(f)
                return [Post.from_dict(post_data) for post_data in data]
        except Exception as e:
            logger.error(f"Erro ao carregar publicações: {e}")
            # Se houver erro, retorna lista vazia e recria o arquivo
            with open(self.posts_file, 'w') as f:
                json.dump([], f)
            return []
    
    def save_posts(self, posts):
        """Salva as publicações com status atualizado"""
        self._ensure_files_exist()
        
        try:
            with open(self.posts_file, 'w') as f:
                json.dump([post.to_dict() for post in posts], f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar publicações: {e}")
            return False
    
    async def send_post(self, bot_instance, post):
        """Envia uma publicação para os grupos configurados usando o bot especificado"""
        if not bot_instance:
            logger.error(f"Bot não inicializado para a publicação {post.id}")
            return False
        
        # Usar grupos da publicação ou grupos padrão do bot
        groups = post.groups
        if not groups:
            # Encontrar o bot correspondente para obter grupos padrão
            bots = self.load_bots()
            bot = next((b for b in bots if b.id == post.bot_id), None)
            if bot:
                groups = bot.default_groups
        
        if not groups:
            logger.warning(f"Nenhum grupo configurado para a publicação {post.id}")
            return False
        
        # Preparar botão inline se configurado
        reply_markup = None
        if post.button_text and post.button_url:
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=post.button_text, url=post.button_url)]
            ])
        
        # Atualizar o status de envio
        now = datetime.now()
        post.last_sent = now
        post.send_status = post.send_status or {}
        post.send_history = post.send_history or {}
        
        # Resultados do envio para cada grupo
        results = {}
        
        for chat_id in groups:
            try:
                # Converter string para int se necessário
                if isinstance(chat_id, str) and chat_id.strip('-').isdigit():
                    chat_id = int(chat_id)
                
                # Se auto_delete estiver ativado, deletar a última mensagem enviada
                if post.auto_delete:
                    await self._delete_last_message(bot_instance, post.id, chat_id)
                
                # Enviar a nova mensagem
                message = None
                if post.media_type == 'photo':
                    message = await bot_instance.send_photo(
                        chat_id=chat_id,
                        photo=post.media_url,
                        caption=post.caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                elif post.media_type == 'video':
                    message = await bot_instance.send_video(
                        chat_id=chat_id,
                        video=post.media_url,
                        caption=post.caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                elif post.media_type == 'text':
                    message = await bot_instance.send_message(
                        chat_id=chat_id,
                        text=post.caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                
                # Registrar o ID da mensagem para possível deleção futura
                if message:
                    # Inicializar histórico para este grupo se não existir
                    if str(chat_id) not in post.send_history:
                        post.send_history[str(chat_id)] = {}
                    
                    # Registrar o ID da mensagem enviada
                    post.send_history[str(chat_id)] = {
                        'message_id': message.message_id,
                        'last_sent': now.isoformat(),
                        'status': 'success'
                    }
                
                # Registrar sucesso
                post.send_status[str(chat_id)] = {
                    "status": "success",
                    "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
                    "message": "Enviado com sucesso"
                }
                results[str(chat_id)] = {"status": "success", "message_id": message.message_id if message else None}
                logger.info(f"Publicação {post.id} enviada para o grupo {chat_id} pelo bot {post.bot_id}")
            
            except TelegramAPIError as e:
                # Registrar erro do Telegram
                error_msg = str(e)
                post.send_status[str(chat_id)] = {
                    "status": "failed",
                    "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
                    "message": f"Erro do Telegram: {error_msg}"
                }
                results[str(chat_id)] = {"status": "error", "error": error_msg}
                logger.error(f"Erro do Telegram ao enviar para o grupo {chat_id}: {e}")
                
                # Registrar falha no histórico
                if str(chat_id) not in post.send_history:
                    post.send_history[str(chat_id)] = {}
                
                post.send_history[str(chat_id)]['status'] = 'error'
                post.send_history[str(chat_id)]['error'] = error_msg
                post.send_history[str(chat_id)]['last_attempt'] = now.isoformat()
            
            except Exception as e:
                # Registrar erro genérico
                error_msg = str(e)
                post.send_status[str(chat_id)] = {
                    "status": "failed",
                    "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
                    "message": f"Erro inesperado: {error_msg}"
                }
                results[str(chat_id)] = {"status": "error", "error": error_msg}
                logger.error(f"Erro inesperado ao enviar para o grupo {chat_id}: {e}")
                
                # Registrar falha no histórico
                if str(chat_id) not in post.send_history:
                    post.send_history[str(chat_id)] = {}
                
                post.send_history[str(chat_id)]['status'] = 'error'
                post.send_history[str(chat_id)]['error'] = error_msg
                post.send_history[str(chat_id)]['last_attempt'] = now.isoformat()
        
        # Atualizar o timestamp do último envio
        self.last_sent[post.id] = time.time()
        
        # Salvar as publicações com status atualizado
        posts = self.load_posts()
        for i, p in enumerate(posts):
            if p.id == post.id:
                posts[i] = post
                break
        self.save_posts(posts)
        
        return {"status": "success", "results": results}
        
    async def _delete_last_message(self, bot_instance, post_id, chat_id):
        """Deleta a última mensagem enviada para um grupo específico"""
        try:
            # Carregar a publicação para obter o histórico
            posts = self.load_posts()
            post = next((p for p in posts if p.id == post_id), None)
            
            if not post or not post.send_history:
                logger.info(f"Nenhum histórico de envio encontrado para a publicação {post_id}")
                return False
            
            # Verificar se há histórico para este grupo
            chat_id_str = str(chat_id)
            if chat_id_str not in post.send_history:
                logger.info(f"Nenhum histórico de envio encontrado para o grupo {chat_id} na publicação {post_id}")
                return False
            
            # Obter o ID da última mensagem enviada
            chat_history = post.send_history[chat_id_str]
            if 'message_id' not in chat_history or chat_history.get('status') != 'success':
                logger.info(f"Nenhuma mensagem válida para deletar no grupo {chat_id}")
                return False
            
            message_id = chat_history['message_id']
            
            # Deletar a mensagem
            await bot_instance.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"Mensagem {message_id} deletada do grupo {chat_id} para a publicação {post_id}")
            
            # Atualizar o histórico
            chat_history['deleted'] = True
            chat_history['deleted_at'] = datetime.now().isoformat()
            
            # Salvar as alterações
            for i, p in enumerate(posts):
                if p.id == post_id:
                    posts[i].send_history[chat_id_str] = chat_history
                    break
            
            self.save_posts(posts)
            return True
        
        except TelegramAPIError as e:
            logger.error(f"Erro do Telegram ao deletar mensagem do grupo {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao deletar mensagem do grupo {chat_id}: {e}")
            return False
    
    async def run_bot(self, bot_id, bot_token):
        """Executa o loop principal de um bot específico"""
        try:
            bot_instance = Bot(token=bot_token)
            self.active_bots[bot_id] = bot_instance
            logger.info(f"Bot {bot_id} inicializado com sucesso")
            
            while self.is_running and bot_id in self.active_bots:
                posts = self.load_posts()
                current_time = time.time()
                
                # Filtrar publicações para este bot
                bot_posts = [post for post in posts if post.bot_id == bot_id]
                
                for post in bot_posts:
                    post_id = post.id
                    interval = int(post.interval_seconds)
                    
                    # Verificar se é hora de enviar esta publicação
                    last_sent = self.last_sent.get(post_id, 0)
                    if current_time - last_sent >= interval:
                        logger.info(f"Enviando publicação {post_id} pelo bot {bot_id}")
                        await self.send_post(bot_instance, post)
                
                # Aguardar um pouco antes de verificar novamente
                await asyncio.sleep(5)
        
        except Exception as e:
            logger.error(f"Erro no loop principal do bot {bot_id}: {e}")
        finally:
            if bot_id in self.active_bots:
                session = await self.active_bots[bot_id].get_session()
                await session.close()
                del self.active_bots[bot_id]
            logger.info(f"Bot {bot_id} finalizado")
    
    def start_bot(self, bot_id):
        """Inicia um bot específico em uma thread separada"""
        if bot_id in self.threads and self.threads[bot_id].is_alive():
            logger.warning(f"Bot {bot_id} já está em execução")
            return False
        
        # Carregar informações do bot
        bots = self.load_bots()
        bot = next((b for b in bots if b.id == bot_id), None)
        
        if not bot:
            logger.error(f"Bot {bot_id} não encontrado")
            return False
        
        if not bot.token:
            logger.error(f"Token não configurado para o bot {bot_id}")
            return False
        
        self.is_running = True
        self.threads[bot_id] = threading.Thread(
            target=self._run_async_loop_for_bot, 
            args=(bot_id, bot.token)
        )
        self.threads[bot_id].daemon = True
        self.threads[bot_id].start()
        
        # Atualizar status do bot
        for i, b in enumerate(bots):
            if b.id == bot_id:
                bots[i].is_active = True
                bots[i].updated_at = datetime.now()
                break
        
        try:
            with open(self.bots_file, 'w') as f:
                json.dump([b.to_dict() for b in bots], f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar status do bot: {e}")
        
        logger.info(f"Bot {bot_id} iniciado")
        return True
    
    def stop_bot(self, bot_id):
        """Para um bot específico"""
        if bot_id not in self.threads or not self.threads[bot_id].is_alive():
            logger.warning(f"Bot {bot_id} não está em execução")
            return False
        
        # Remover o bot da lista de ativos para que o loop termine
        if bot_id in self.active_bots:
            del self.active_bots[bot_id]
        
        # Aguardar a thread terminar
        self.threads[bot_id].join(timeout=5)
        del self.threads[bot_id]
        
        # Atualizar status do bot
        bots = self.load_bots()
        for i, b in enumerate(bots):
            if b.id == bot_id:
                bots[i].is_active = False
                bots[i].updated_at = datetime.now()
                break
        
        try:
            with open(self.bots_file, 'w') as f:
                json.dump([b.to_dict() for b in bots], f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar status do bot: {e}")
        
        logger.info(f"Bot {bot_id} parado")
        return True
    
    def start_all_bots(self):
        """Inicia todos os bots cadastrados"""
        bots = self.load_bots()
        success_count = 0
        
        for bot in bots:
            if self.start_bot(bot.id):
                success_count += 1
        
        return success_count
    
    def stop_all_bots(self):
        """Para todos os bots em execução"""
        bot_ids = list(self.threads.keys())
        success_count = 0
        
        for bot_id in bot_ids:
            if self.stop_bot(bot_id):
                success_count += 1
        
        return success_count
    
    def _run_async_loop_for_bot(self, bot_id, bot_token):
        """Executa o loop assíncrono para um bot específico em uma thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run_bot(bot_id, bot_token))
        finally:
            loop.close()
    
    def status(self):
        """Retorna o status atual dos bots"""
        bots = self.load_bots()
        posts = self.load_posts()
        
        return {
            "active_bots": [b.id for b in bots if b.is_active],
            "total_bots": len(bots),
            "total_posts": len(posts),
            "running_threads": list(self.threads.keys()),
            "last_sent": {post_id: datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') 
                         for post_id, timestamp in self.last_sent.items()}
        }
