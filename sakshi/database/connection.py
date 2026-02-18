"""
Database connection management.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/goec")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from database.models import Camera, Detection, UsecaseResult, Alert, AnalyticsDaily
    
    print(f"[DATABASE] Initializing database...")
    print(f"[DATABASE] Database URL: {DATABASE_URL.split('@')[-1]}")  # Hide credentials
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print(f"[DATABASE] Tables created successfully")
        
        # Test connection
        with engine.connect() as conn:
            print(f"[DATABASE] Connection test successful")
    except Exception as e:
        print(f"[DATABASE] Error initializing database: {str(e)}")
        raise
