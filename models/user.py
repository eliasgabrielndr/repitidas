from datetime import datetime
import uuid
import hashlib

class User:
    def __init__(self, id=None, username=None, password=None, is_admin=False, post_limit=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.username = username
        self.password = password  # Deve ser armazenado como hash
        self.is_admin = is_admin
        self.post_limit = post_limit  # Limite de publicações que o usuário pode criar
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'password': self.password,
            'is_admin': self.is_admin,
            'post_limit': self.post_limit,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get('id'),
            username=data.get('username'),
            password=data.get('password'),
            is_admin=data.get('is_admin', False),
            post_limit=data.get('post_limit'),
            created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data.get('updated_at')) if data.get('updated_at') else None
        )
    
    @staticmethod
    def hash_password(password):
        """Cria um hash seguro da senha"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado"""
        password_hash = self.hash_password(password)
        return self.password == password_hash
