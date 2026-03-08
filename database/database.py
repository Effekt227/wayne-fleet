"""
Database Connection - Wayne Fleet Management System
SQLAlchemy setup and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base
import os

# Dual-mode: PostgreSQL v cloudu (env DATABASE_URL), SQLite lokálně
_cloud_url = os.environ.get('DATABASE_URL', '')
if _cloud_url:
    # Supabase vrací "postgres://" ale SQLAlchemy potřebuje "postgresql+pg8000://"
    if _cloud_url.startswith('postgres://'):
        _cloud_url = _cloud_url.replace('postgres://', 'postgresql+pg8000://', 1)
    elif _cloud_url.startswith('postgresql://'):
        _cloud_url = _cloud_url.replace('postgresql://', 'postgresql+pg8000://', 1)
    DATABASE_URL = _cloud_url
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"ssl_context": True})
    DB_PATH = '(PostgreSQL cloud)'
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), 'wayne_fleet.db')
    DATABASE_URL = f'sqlite:///{DB_PATH}'
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Scoped session for thread safety
db_session = scoped_session(SessionLocal)


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at: {DB_PATH}")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def drop_all():
    """Drop all tables - USE WITH CAUTION"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All tables dropped!")
