import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ada.api.v1 import auth as auth_mod
from ada.db.models import Base
from ada.db.session import get_db
from ada.main import app

# STEPS 1-2 (active): login, workspaces, dashboard, runs.
# STEP 3+: delete a line below to switch that step's tests back on.
collect_ignore = [
    "unit/test_pipeline.py",   # analyse + escalation pipeline
    "unit/test_baseline.py",   # scoring baseline
    "unit/test_labeler.py",    # winner / watch / dog labels
]


@pytest.fixture()
def client():
    """Fresh in-memory database per test; yields (TestClient, Session factory)."""
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    Session = sessionmaker(eng, expire_on_commit=False)

    def override():
        with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override
    for bucket in (auth_mod._FAILS, auth_mod._RESET_MAILS, auth_mod._RESET_IPS):
        bucket.clear()
    yield TestClient(app), Session
    app.dependency_overrides.clear()
