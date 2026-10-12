import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ada.api.v1 import auth as auth_mod
from ada.db.models import Base
from ada.db.session import get_db
from ada.main import app
from ada.security.tokens import make_reset_token


@pytest.fixture()
def client():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    Session = sessionmaker(eng, expire_on_commit=False)

    def override():
        with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override
    auth_mod._FAILS.clear()
    yield TestClient(app), Session
    app.dependency_overrides.clear()


def signup(c, email="A@Example.com", pw="password123"):
    return c.post("/api/v1/auth/signup", json={"email": email, "password": pw})


def test_signup_login_me_logout(client):
    c, _ = client
    assert signup(c).status_code == 201
    assert c.get("/api/v1/auth/me").json()["email"] == "a@example.com"   # normalised, signed in
    c.post("/api/v1/auth/logout")
    assert c.get("/api/v1/auth/me").status_code == 401
    assert c.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"}).status_code == 200


def test_duplicate_and_weak_password(client):
    c, _ = client
    signup(c)
    assert signup(c).status_code == 409
    assert signup(c, "b@example.com", "short").status_code == 422


def test_wrong_password_and_throttle(client):
    c, _ = client
    signup(c)
    bad = {"email": "a@example.com", "password": "nope"}
    for _ in range(5):
        assert c.post("/api/v1/auth/login", json=bad).status_code == 401
    assert c.post("/api/v1/auth/login", json=bad).status_code == 429


def test_forgot_password_does_not_reveal_accounts(client):
    c, _ = client
    signup(c)
    a = c.post("/api/v1/auth/forgot-password", json={"email": "a@example.com"}).json()
    b = c.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}).json()
    assert a == b


def test_reset_flow_and_single_use(client):
    c, Session = client
    signup(c)
    from ada.db.models import User
    with Session() as s:
        u = s.query(User).one()
        token = make_reset_token(u.id, u.password_hash)
    r = c.post("/api/v1/auth/reset-password", json={"token": token, "password": "newpassword1"})
    assert r.status_code == 200
    assert c.post("/api/v1/auth/reset-password", json={"token": token, "password": "another-pass1"}).status_code == 400
    assert c.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "newpassword1"}).status_code == 200
    assert c.post("/api/v1/auth/reset-password", json={"token": "garbage", "password": "newpassword1"}).status_code == 400
