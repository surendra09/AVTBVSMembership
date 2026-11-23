from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {"pool_pre_ping": True, "echo": settings.DB_ECHO, "future": True}
    if url.startswith("mysql"):
        kwargs.update(pool_size=settings.DB_POOL_SIZE, max_overflow=20, pool_recycle=1800)
    elif url.startswith("sqlite"):
        # Local/demo fallback: allow pooled connections to be shared across the
        # request threadpool and the in-process notification worker thread.
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


engine = create_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
