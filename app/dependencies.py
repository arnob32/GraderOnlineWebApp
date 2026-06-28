# dependencies.py
# Re-exports get_db so routes can import from here instead of database.py
from app.database import get_db

__all__ = ["get_db"]