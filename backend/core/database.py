from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        from core.config import get_settings
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
            poolclass=StaticPool if "sqlite" in settings.database_url else None,
        )
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=get_engine())


Base = declarative_base()


def SessionLocal():
    return get_session_local()()


engine = None


def get_engine_property():
    global engine
    if engine is None:
        engine = get_engine()
    return engine