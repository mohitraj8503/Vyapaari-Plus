from sqlalchemy.orm import Session

from app.modules.business.models import BusinessProfile


class BusinessRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active(self) -> BusinessProfile | None:
        return self.db.query(BusinessProfile).filter(BusinessProfile.is_active.is_(True)).first()
