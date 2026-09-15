"""
schemas/price.py
-----------------
Response shape for prices. Numeric money fields (current_price etc.)
are typed as `Decimal` so precision is preserved all the way out to
the JSON response — matching how they're stored in the database
(see models/price.py for why we use Numeric/Decimal for money).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PriceOut(BaseModel):
    material_id: str
    current_price: Decimal
    min_price: Decimal
    max_price: Decimal
    unit: str
    currency: str
    updated_at: datetime

    model_config = {"from_attributes": True}
