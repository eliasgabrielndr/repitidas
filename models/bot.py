from datetime import datetime

class Bot:
    def __init__(self, id=None, name=None, token=None, default_groups=None, 
                 is_active=False, created_at=None, updated_at=None):
        self.id = id
        self.name = name
        self.token = token
        self.default_groups = default_groups or []
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'token': self.token,
            'default_groups': self.default_groups,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            token=data.get('token'),
            default_groups=data.get('default_groups', []),
            is_active=data.get('is_active', False),
            created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data.get('updated_at')) if data.get('updated_at') else None
        )
