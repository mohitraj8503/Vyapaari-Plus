from decimal import Decimal
from uuid import uuid4

from app.core.exceptions import ValidationError
from app.modules.customers.models import Customer, CustomerEntryType, CustomerLedgerEntry
from app.modules.customers.repository import CustomerRepository


class CustomerLedgerService:
    def __init__(self, db):
        self.db = db
        self.repository = CustomerRepository(db)

    def create_customer(self, name, phone=None, credit_limit=Decimal("0.00")):
        if not (name or "").strip():
            raise ValidationError("Customer name is required.")
        limit = Decimal(str(credit_limit))
        if limit < 0:
            raise ValidationError("Credit limit cannot be negative.")
        customer = Customer(id=str(uuid4()), name=name.strip(), phone=phone, credit_limit=limit)
        self.db.add(customer)
        self.db.commit()
        return customer

    def record_sale(self, customer_id, amount, invoice_id=None):
        amount = Decimal(str(amount))
        customer = self.db.get(Customer, customer_id)
        if customer is None or amount <= 0:
            raise ValidationError("Customer and positive amount are required.")
        if customer.credit_limit and self.balance(customer_id) + amount > customer.credit_limit:
            raise ValidationError("Customer credit limit exceeded.")
        self.db.add(CustomerLedgerEntry(
            id=str(uuid4()), customer_id=customer_id, invoice_id=invoice_id,
            entry_type=CustomerEntryType.SALE, amount=amount, description="Credit sale",
        ))

    def record_payment(self, customer_id, amount, description="Customer payment"):
        amount = Decimal(str(amount))
        balance = self.balance(customer_id)
        if amount <= 0 or amount > balance:
            raise ValidationError("Payment must be positive and not exceed balance.")
        entry = CustomerLedgerEntry(
            id=str(uuid4()), customer_id=customer_id, entry_type=CustomerEntryType.PAYMENT,
            amount=amount, description=description,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def record_reversal(self, customer_id, amount, invoice_id=None):
        self.db.add(CustomerLedgerEntry(
            id=str(uuid4()), customer_id=customer_id, invoice_id=invoice_id,
            entry_type=CustomerEntryType.REVERSAL, amount=Decimal(str(amount)),
            description="Invoice reversal",
        ))

    def balance(self, customer_id):
        return self.repository.balance(customer_id)

    def statement(self, customer_id):
        running = Decimal("0.00")
        rows = []
        for entry in self.repository.entries(customer_id):
            running += entry.signed_amount
            rows.append({"entry": entry, "balance": running})
        return rows
