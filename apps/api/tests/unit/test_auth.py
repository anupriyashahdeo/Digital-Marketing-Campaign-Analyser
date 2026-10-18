from ada.api.v1 import auth as auth_mod
from ada.security.tokens import make_reset_token


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


def test_forgot_password_emails_reset_link(client, monkeypatch):
    c, _ = client
    signup(c)
    sent = []
    monkeypatch.setattr(auth_mod.mailer, "send", lambda to, subject, body: sent.append((to, body)))
    c.post("/api/v1/auth/forgot-password", json={"email": "a@example.com"})
    c.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert len(sent) == 1
    assert sent[0][0] == "a@example.com" and "/reset-password?token=" in sent[0][1]


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


def test_reset_signs_out_existing_sessions(client):
    c, Session = client
    signup(c)                                     # c now holds a session cookie
    assert c.get("/api/v1/auth/me").status_code == 200
    from ada.db.models import User
    with Session() as s:
        u = s.query(User).one()
        token = make_reset_token(u.id, u.password_hash)
    c.post("/api/v1/auth/reset-password", json={"token": token, "password": "newpassword1"})
    assert c.get("/api/v1/auth/me").status_code == 401   # old cookie no longer works


def test_forgot_password_caps_emails_per_account(client, monkeypatch):
    c, _ = client
    signup(c)
    sent = []
    monkeypatch.setattr(auth_mod.mailer, "send", lambda to, subject, body: sent.append(to))
    msgs = {c.post("/api/v1/auth/forgot-password", json={"email": "a@example.com"}).text for _ in range(5)}
    assert len(sent) == 3 and len(msgs) == 1     # extra requests are dropped silently


def test_forgot_password_throttles_per_ip(client):
    c, _ = client
    for i in range(20):
        assert c.post("/api/v1/auth/forgot-password", json={"email": f"x{i}@example.com"}).status_code == 200
    assert c.post("/api/v1/auth/forgot-password", json={"email": "y@example.com"}).status_code == 429


# Sign-in checks for workspace and run routes live in test_workspaces.py
