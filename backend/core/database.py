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


class _SessionLocalCallable:
    def __call__(self):
        return get_session_local()()

    def __iter__(self):
        return iter(get_session_local()())


SessionLocal = _SessionLocalCallable()


class _EngineProperty:
    @property
    def url(self):
        return get_engine().url


engine = _EngineProperty()