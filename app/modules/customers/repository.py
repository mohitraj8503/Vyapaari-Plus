from sqlalchemy.orm import Session

from app.modules.customers.models import CustomerLedgerEntry


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def balance(self, customer_id):
        entries = self.db.query(CustomerLedgerEntry).filter(CustomerLedgerEntry.customer_id == customer_id).all()
        return sum((entry.signed_amount for entry in entries), start=0)

    def entries(self, customer_id):
        return self.db.query(CustomerLedgerEntry).filter(
            CustomerLedgerEntry.customer_id == customer_id
        ).order_by(CustomerLedgerEntry.entry_date, CustomerLedgerEntry.created_at).all()
