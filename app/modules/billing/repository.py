from sqlalchemy.orm import Session

from app.modules.billing.models import SalesInvoice


class BillingRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_idempotency_key(self, key: str):
        return self.db.query(SalesInvoice).filter(SalesInvoice.idempotency_key == key).first()

    def by_number(self, number: str):
        return self.db.query(SalesInvoice).filter(SalesInvoice.invoice_number == number).first()
