"""
scripts/seed.py
----------------
Populates the database with fake demo data so you have something to
test against during development: collectors, recyclers, an admin,
materials, prices, a few sample lots, and a sample transaction.

Run this AFTER create_tables.py:

    python scripts/create_tables.py
    python scripts/seed.py

Safe to re-run: it clears existing demo rows first (see `wipe_data()`)
so you don't end up with duplicates every time you run it.

All emails/phones/names here are clearly fake, for demo purposes only.
"""

import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, Base, engine
import app.models  # noqa: F401  (registers all models)
from app.models.user import User, UserRole
from app.models.material import Material
from app.models.price import Price
from app.models.recycler import Recycler
from app.models.lot import Lot, LotCondition, LotStatus
from app.models.transaction import Transaction
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.pickup import Pickup
from app.models.handover import Handover
from app.models.recycler import recycler_materials
from app.models.notification import Notification


def wipe_data(db):
    """
    Deletes existing rows from all tables before reseeding, so running
    this script multiple times doesn't create duplicate demo data.

    Order matters here: we delete "child" tables (the ones with foreign
    keys pointing to other tables) before "parent" tables, otherwise the
    database will reject the delete due to foreign key constraints.

    Full dependency chain, deepest child first:
      Notification, Payment  -> Transaction
      Transaction            -> Lot, Recycler
      Handover                -> Pickup, Lot, Recycler
      Pickup                  -> Lot, Recycler
      recycler_materials      -> Recycler, Material  (join table)
      Recycler                -> User
      Lot                     -> User, Material
      Price                   -> Material
      Material, User           (no dependencies)
    """
    print("Clearing existing data...")
    db.query(Notification).delete()
    db.query(Payment).delete()
    db.query(Transaction).delete()
    db.query(Handover).delete()
    db.query(Pickup).delete()
    db.execute(recycler_materials.delete())  # join table: no ORM model, delete via the Table object
    db.query(Recycler).delete()
    db.query(Lot).delete()
    db.query(Price).delete()
    db.query(Material).delete()
    db.query(User).delete()
    db.commit()


def seed_materials(db):
    print("Seeding materials...")
    materials_data = [
        ("MAT001", "copper", "Copper", "copper-icon", "kg"),
        ("MAT002", "aluminium", "Aluminium", "aluminium-icon", "kg"),
        ("MAT003", "pcb", "PCB", "pcb-icon", "kg"),
        ("MAT004", "lcd", "LCD", "lcd-icon", "kg"),
        ("MAT005", "crt", "CRT", "crt-icon", "kg"),
        ("MAT006", "battery", "Battery", "battery-icon", "kg"),
        ("MAT007", "cable", "Cable", "cable-icon", "kg"),
        ("MAT008", "plastic", "Plastic", "plastic-icon", "kg"),
        ("MAT009", "other", "Other", "other-icon", "kg"),
    ]
    materials = {}
    for mat_id, name, display_name, icon, unit in materials_data:
        material = Material(id=mat_id, name=name, display_name=display_name, icon=icon, unit=unit)
        db.add(material)
        materials[mat_id] = material
    db.commit()
    return materials


def seed_prices(db):
    print("Seeding prices...")
    # (material_id, current_price, min_price, max_price)  -- INR per kg
    prices_data = [
        ("MAT001", 650, 600, 700),    # Copper
        ("MAT002", 180, 150, 200),    # Aluminium
        ("MAT003", 450, 400, 500),    # PCB
        ("MAT004", 90, 70, 110),      # LCD
        ("MAT005", 40, 30, 50),       # CRT
        ("MAT006", 120, 100, 140),    # Battery
        ("MAT007", 220, 200, 250),    # Cable
        ("MAT008", 25, 20, 35),       # Plastic
        ("MAT009", 15, 10, 20),       # Other
    ]
    prices = {}
    for material_id, current, min_p, max_p in prices_data:
        price = Price(
            material_id=material_id,
            current_price=Decimal(current),
            min_price=Decimal(min_p),
            max_price=Decimal(max_p),
            unit="kg",
            currency="INR",
        )
        db.add(price)
        prices[material_id] = price
    db.commit()
    return prices


def seed_users(db):
    print("Seeding users (collectors, recyclers, admin)...")

    collectors = [
        User(email="collector@test.com", phone="9000000001", name="Ravi Kumar", role=UserRole.COLLECTOR),
        User(email="collector2@test.com", phone="9000000002", name="Sita Devi", role=UserRole.COLLECTOR),
        User(email="collector3@test.com", phone="9000000003", name="Arjun Singh", role=UserRole.COLLECTOR),
    ]
    for c in collectors:
        db.add(c)

    recycler_users = [
        User(email="recycler@test.com", phone="9000000010", name="GreenCycle Traders", role=UserRole.RECYCLER),
        User(email="recycler2@test.com", phone="9000000011", name="EcoScrap Solutions", role=UserRole.RECYCLER),
    ]
    for r in recycler_users:
        db.add(r)

    admin = User(email="admin@test.com", phone="9000000099", name="Admin User", role=UserRole.ADMIN)
    db.add(admin)

    db.commit()
    return {
        "collectors": collectors,
        "recycler_users": recycler_users,
        "admin": admin,
    }


def seed_recyclers(db, recycler_users, materials):
    print("Seeding recycler business profiles...")

    recycler1 = Recycler(
        user_id=recycler_users[0].id,
        name="GreenCycle Traders",
        authorized=True,
        latitude=12.9716,
        longitude=77.5946,  # Bengaluru
        service_radius_km=15.0,
        pickup_available=True,
        reliability_score=4.5,
    )
    recycler1.accepted_materials = [
        materials["MAT001"], materials["MAT002"], materials["MAT003"], materials["MAT007"]
    ]
    db.add(recycler1)

    recycler2 = Recycler(
        user_id=recycler_users[1].id,
        name="EcoScrap Solutions",
        authorized=True,
        latitude=12.9352,
        longitude=77.6146,  # a few km away, also Bengaluru
        service_radius_km=10.0,
        pickup_available=True,
        reliability_score=4.0,
    )
    recycler2.accepted_materials = [
        materials["MAT004"], materials["MAT005"], materials["MAT006"], materials["MAT008"], materials["MAT009"]
    ]
    db.add(recycler2)

    db.commit()
    return [recycler1, recycler2]


def seed_lots(db, collectors, materials, prices):
    print("Seeding sample lots...")

    lot1 = Lot(
        collector_id=collectors[0].id,
        material_id="MAT001",  # Copper
        estimated_weight=10.5,
        condition=LotCondition.GOOD,
        estimated_value=Decimal("10.5") * prices["MAT001"].current_price,
        status=LotStatus.CREATED,
        latitude=12.9716,
        longitude=77.5946,
        photo_url="https://example.com/photo1.jpg",
    )
    lot2 = Lot(
        collector_id=collectors[1].id,
        material_id="MAT003",  # PCB
        estimated_weight=3.2,
        condition=LotCondition.MIXED,
        estimated_value=Decimal("3.2") * prices["MAT003"].current_price,
        status=LotStatus.CREATED,
        latitude=12.9352,
        longitude=77.6146,
        photo_url="https://example.com/photo2.jpg",
    )
    lot3 = Lot(
        collector_id=collectors[2].id,
        material_id="MAT008",  # Plastic
        estimated_weight=25.0,
        condition=LotCondition.DAMAGED,
        estimated_value=Decimal("25.0") * prices["MAT008"].current_price,
        status=LotStatus.COMPLETED,
        latitude=12.9600,
        longitude=77.6000,
        photo_url="https://example.com/photo3.jpg",
        actual_weight=24.0,
    )
    db.add_all([lot1, lot2, lot3])
    db.commit()
    return [lot1, lot2, lot3]


def seed_transactions(db, lots, recyclers):
    print("Seeding a sample transaction...")

    # lot3 is COMPLETED, so it gets a matching transaction — this mirrors
    # what the handover_service will do automatically in Phase 8.
    completed_lot = lots[2]
    transaction = Transaction(
        lot_id=completed_lot.id,
        collector_id=completed_lot.collector_id,
        recycler_id=recyclers[1].id,
        material_name="Plastic",
        weight=completed_lot.actual_weight,
        amount=Decimal("600.00"),
        payment_method=PaymentMethod.CASH,
        payment_status=PaymentStatus.PAID,
    )
    db.add(transaction)
    db.commit()


def main():
    # Make sure tables exist before seeding (harmless if they already do).
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        wipe_data(db)
        materials = seed_materials(db)
        prices = seed_prices(db)
        users = seed_users(db)
        recyclers = seed_recyclers(db, users["recycler_users"], materials)
        lots = seed_lots(db, users["collectors"], materials, prices)
        seed_transactions(db, lots, recyclers)

        print("\nSeed complete! Demo accounts you can use:")
        print("  collector@test.com  (role: COLLECTOR)")
        print("  recycler@test.com   (role: RECYCLER)")
        print("  admin@test.com      (role: ADMIN)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
