"""Test configuration. Tests run against a real MySQL database (TEST_DATABASE_URL)."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="avtbvs-test-")
os.environ.setdefault("TEST_DATABASE_URL",
                      "mysql+pymysql://avtbvs:devpassword@127.0.0.1:3306/avtbvs_test?charset=utf8mb4")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["ENVIRONMENT"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["NOTIFICATION_WORKER_ENABLED"] = "false"
os.environ["PRIVATE_STORAGE_DIR"] = os.path.join(_tmp, "private")
os.environ["CONSOLE_OUTBOX_FILE"] = os.path.join(_tmp, "outbox.log")
os.environ["MEMBERSHIP_NUMBER_TEMPLATE"] = "{seq}"

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.rate_limit import limiter  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean():
    yield
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    limiter.reset()


@pytest.fixture
def db():
    # READ COMMITTED so assertions see rows committed by the API after the test's first read
    with SessionLocal(bind=engine.execution_options(isolation_level="READ COMMITTED")) as session:
        yield session
