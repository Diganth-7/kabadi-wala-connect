"""
database.py
------------
Sets up the connection to PostgreSQL using SQLAlchemy.

Key concepts (since you're new to backend dev):

- `engine`      -> The actual connection to the PostgreSQL database.
- `SessionLocal`-> A factory that creates new "sessions" (a session is
                    like a temporary workspace you use to talk to the DB
                    — query, insert, update, etc.).
- `Base`        -> A special class that all our database models
                    (User, Lot, Recycler, etc. — added in Phase 2) will
                    inherit from. SQLAlchemy uses it to know which
                    Python classes map to which database tables.
- `get_db()`    -> A FastAPI "dependency". Every API endpoint that needs
                    to talk to the database will use this function to
                    get a session, and it automatically closes the
                    session when the request is done — even if an error
                    happens. This prevents connection leaks.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# The engine manages the actual pool of connections to Postgres.
engine = create_engine(settings.DATABASE_URL)

# Each instance of SessionLocal() is a new database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models (created in Phase 2) will inherit from this Base class.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session to path functions.

    Usage in a router:

        @router.get("/materials")
        def list_materials(db: Session = Depends(get_db)):
            ...

    The `yield` pattern ensures the session is always closed after the
    request finishes, whether it succeeded or raised an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
