from uuid import uuid4

from app.core.exceptions import ValidationError
from app.modules.business.models import BusinessProfile
from app.modules.business.repository import BusinessRepository
from app.modules.gst.models import verify_gstin_checksum
from app.modules.gst.states import STATE_CODES, normalize_state_code


class BusinessService:
    def __init__(self, db):
        self.db = db
        self.repository = BusinessRepository(db)

    def create_or_update(self, *, name, state_code, address, gstin=None,
                         financial_year_start_month=4, invoice_prefix="INV"):
        name = (name or "").strip()
        address = (address or "").strip()
        code = normalize_state_code(state_code)
        prefix = (invoice_prefix or "").strip().upper()
        if not name or not address:
            raise ValidationError("Business name and address are required.")
        if code not in STATE_CODES:
            raise ValidationError("Invalid business state code.")
        if gstin:
            gstin = gstin.strip().upper()
            if not verify_gstin_checksum(gstin) or gstin[:2] != code:
                raise ValidationError("GSTIN is invalid or does not match state code.")
        if not 1 <= int(financial_year_start_month) <= 12:
            raise ValidationError("Financial year start month must be 1-12.")
        if not prefix.isalnum() or len(prefix) > 8:
            raise ValidationError("Invoice prefix must be alphanumeric and at most 8 characters.")
        profile = self.repository.get_active()
        if profile is None:
            profile = BusinessProfile(id=str(uuid4()))
            self.db.add(profile)
        profile.name = name
        profile.gstin = gstin
        profile.state_code = code
        profile.address = address
        profile.financial_year_start_month = int(financial_year_start_month)
        profile.invoice_prefix = prefix
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get(self):
        profile = self.repository.get_active()
        if profile is None:
            raise ValidationError("Business profile is not configured.")
        return profile
