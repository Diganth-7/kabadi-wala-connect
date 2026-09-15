"""
scripts/create_tables.py
-------------------------
Creates all database tables based on our SQLAlchemy models.

Run this ONCE (and again any time you add a new model) to set up your
PostgreSQL database schema:

    python scripts/create_tables.py

Note: For a real production app you'd normally use a migration tool
like Alembic instead of create_all(), so you can version and roll back
schema changes. For this prototype, create_all() is simpler and enough
— we're not over-engineering a student project with a migration system
it doesn't need yet.
"""

import sys
import os

# Allow running this script directly (python scripts/create_tables.py)
# by adding the project root to Python's import path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, engine
import app.models  # noqa: F401  (import registers all models on Base.metadata)


def main():
    print("Creating all tables in the database...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")


if __name__ == "__main__":
    main()
