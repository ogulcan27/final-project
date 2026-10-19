import pytest

from app import db


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Point the DB at a temp file and initialize it."""
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "sub" / "test.db"))
    db.init_db()
