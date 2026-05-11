from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from loguru import logger

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


def _run_migrations():
    engine = get_engine()
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("prediction_logs")}
    migrations = [
        ("shap_values", "ALTER TABLE prediction_logs ADD COLUMN shap_values TEXT"),
        ("top_features", "ALTER TABLE prediction_logs ADD COLUMN top_features TEXT"),
        ("explanation_latency", "ALTER TABLE prediction_logs ADD COLUMN explanation_latency FLOAT"),
    ]
    with engine.connect() as conn:
        for col_name, stmt in migrations:
            if col_name not in existing_columns:
                try:
                    conn.execute(text(stmt))
                    logger.info(f"Migrated prediction_logs: added column {col_name}")
                except Exception as e:
                    logger.warning(f"Migration for {col_name} failed: {e}")
        conn.commit()


def init_db():
    Base.metadata.create_all(bind=get_engine())
    _run_migrations()


Base = declarative_base()


def SessionLocal():
    return get_session_local()()


engine = None


def get_engine_property():
    global engine
    if engine is None:
        engine = get_engine()
    return engine