from datetime import datetime

class Post:
    def __init__(self, id=None, bot_id=None, media_type=None, media_url=None, caption=None, 
                 button_text=None, button_url=None, interval_seconds=None, 
                 groups=None, created_at=None, updated_at=None, last_sent=None, 
                 send_status=None, auto_delete=False, user_id=None, active=True, click_count=0,
                 send_history=None):
        self.id = id
        self.bot_id = bot_id  # ID do bot que enviará esta publicação
        self.media_type = media_type  # 'photo', 'video' ou 'text'
        self.media_url = media_url
        self.caption = caption
        self.button_text = button_text
        self.button_url = button_url
        self.interval_seconds = interval_seconds
        self.groups = groups or []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.last_sent = last_sent  # Timestamp do último envio
        self.send_status = send_status or {}  # Status de envio para cada grupo
        self.auto_delete = auto_delete  # Opção para deletar automaticamente a última publicação antes de enviar nova
        self.user_id = user_id  # ID do usuário que criou a publicação
        self.active = active  # Se a publicação está ativa para envio
        self.click_count = click_count  # Contador de cliques na publicação
        self.send_history = send_history or {}  # Histórico de envios com IDs das mensagens para deleção
    
    def to_dict(self):
        return {
            'id': self.id,
            'bot_id': self.bot_id,
            'media_type': self.media_type,
            'media_url': self.media_url,
            'caption': self.caption,
            'button_text': self.button_text,
            'button_url': self.button_url,
            'interval_seconds': self.interval_seconds,
            'groups': self.groups,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_sent': self.last_sent.isoformat() if self.last_sent else None,
            'send_status': self.send_status,
            'auto_delete': self.auto_delete,
            'user_id': self.user_id,
            'active': self.active,
            'click_count': self.click_count,
            'send_history': self.send_history
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get('id'),
            bot_id=data.get('bot_id'),
            media_type=data.get('media_type'),
            media_url=data.get('media_url'),
            caption=data.get('caption'),
            button_text=data.get('button_text'),
            button_url=data.get('button_url'),
            interval_seconds=data.get('interval_seconds'),
            groups=data.get('groups', []),
            created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data.get('updated_at')) if data.get('updated_at') else None,
            last_sent=datetime.fromisoformat(data.get('last_sent')) if data.get('last_sent') else None,
            send_status=data.get('send_status', {}),
            auto_delete=data.get('auto_delete', False),
            user_id=data.get('user_id'),
            active=data.get('active', True),
            click_count=data.get('click_count', 0),
            send_history=data.get('send_history', {})
        )
