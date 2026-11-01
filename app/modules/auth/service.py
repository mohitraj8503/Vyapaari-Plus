import secrets
from uuid import uuid4

from app.core.exceptions import ValidationError
from app.core.security import hash_password, verify_password
from app.modules.auth.models import Role, User
from app.modules.auth.repository import AuthRepository

ROLE_PERMISSIONS = {
    Role.OWNER: {"billing", "inventory", "transfers", "reports", "business"},
    Role.MANAGER: {"billing", "inventory", "transfers", "reports"},
    Role.CASHIER: {"billing"},
}


class AuthService:
    _tokens = {}

    def __init__(self, db):
        self.db = db
        self.repository = AuthRepository(db)

    def create_user(self, username, password, role=Role.CASHIER):
        if not username or len(password or "") < 8:
            raise ValidationError("Username and password of at least 8 characters are required.")
        if self.repository.by_username(username):
            raise ValidationError("Username already exists.")
        hashed, salt = hash_password(password)
        user = User(id=str(uuid4()), username=username, password_hash=hashed,
                    password_salt=salt, role=Role(role))
        self.db.add(user)
        self.db.commit()
        return user

    def login(self, username, password):
        user = self.repository.by_username(username)
        if user is None or not user.is_active or not verify_password(password, user.password_hash, user.password_salt):
            raise ValidationError("Invalid credentials.")
        token = secrets.token_urlsafe(32)
        AuthService._tokens[token] = user.id
        return token

    def require(self, token, permission):
        user_id = AuthService._tokens.get(token)
        user = self.db.get(User, user_id) if user_id else None
        if user is None or permission not in ROLE_PERMISSIONS[user.role]:
            raise ValidationError("Permission denied.")
        return user
