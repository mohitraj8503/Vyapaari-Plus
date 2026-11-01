from app.modules.auth.models import User


class AuthRepository:
    def __init__(self, db):
        self.db = db

    def by_username(self, username):
        return self.db.query(User).filter(User.username == username).first()
