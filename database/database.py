"""
Database Connection - Wayne Fleet Management System
SQLAlchemy setup and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL as SA_URL
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base
import os
from urllib.parse import urlparse

# Dual-mode: PostgreSQL v cloudu (env DATABASE_URL nebo st.secrets), SQLite lokálně
_cloud_url = os.environ.get('DATABASE_URL', '')
if not _cloud_url:
    try:
        import streamlit as st
        _cloud_url = st.secrets.get('DATABASE_URL', '')
    except Exception:
        pass
if _cloud_url:
    # Parsujeme URL a předáme parametry explicitně (pg8000 ořezává username na tečce)
    _parsed = urlparse(_cloud_url)
    _sa_url = SA_URL.create(
        drivername="postgresql+pg8000",
        username=_parsed.username,
        password=_parsed.password,
        host=_parsed.hostname,
        port=_parsed.port,
        database=_parsed.path.lstrip('/'),
    )
    DATABASE_URL = str(_sa_url)
    engine = create_engine(
        _sa_url,
        echo=False,
        connect_args={"ssl_context": True},
        pool_size=3,
        max_overflow=2,
        pool_pre_ping=True,
        pool_recycle=300,
    )
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
