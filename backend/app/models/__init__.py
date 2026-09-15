"""
models/__init__.py
-------------------
Importing every model here ensures that when something does
`from app.database import Base` and then `Base.metadata.create_all(...)`,
SQLAlchemy already knows about ALL our tables -- not just the ones that
happened to be imported elsewhere first.

Just `import app.models` anywhere before calling create_all() and every
table below will be registered.
"""

from app.models.user import User, UserRole
from app.models.material import Material
from app.models.price import Price
from app.models.recycler import Recycler, recycler_materials
from app.models.lot import Lot, LotCondition, LotStatus
from app.models.pickup import Pickup, PickupStatus
from app.models.handover import Handover
from app.models.transaction import Transaction
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.notification import Notification

__all__ = [
    "User", "UserRole",
    "Material",
    "Price",
    "Recycler", "recycler_materials",
    "Lot", "LotCondition", "LotStatus",
    "Pickup", "PickupStatus",
    "Handover",
    "Transaction",
    "Payment", "PaymentMethod", "PaymentStatus",
    "Notification",
]
