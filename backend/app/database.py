"""Database engine and session management.

The engine is configured with a connection pool sized for horizontal scaling:
every API worker keeps a small pool, and many workers can run behind a load
balancer. SQLite (dev) ignores pool settings and needs check_same_thread=False.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

if settings.is_sqlite:
    engine = create_engine(
        settings.sqlalchemy_database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    # pysqlite's DBAPI driver runs its own implicit transaction management
    # (opens a transaction on the first DML, autocommits on non-DML) that
    # fights with SQLAlchemy's own BEGIN/SAVEPOINT control — most visibly,
    # nested SAVEPOINTs used for test isolation (see tests/conftest.py's `db`
    # fixture) silently stop rolling back correctly after the first commit.
    # This is SQLAlchemy's documented workaround: disable pysqlite's implicit
    # handling and let SQLAlchemy issue BEGIN itself. Postgres (prod) isn't
    # affected — this whole branch only runs for settings.is_sqlite.
    @event.listens_for(engine, "connect")
    def _sqlite_disable_pysqlite_transactions(dbapi_connection, _record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _sqlite_emit_begin(conn):
        conn.exec_driver_sql("BEGIN")
else:
    engine = create_engine(
        settings.sqlalchemy_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
