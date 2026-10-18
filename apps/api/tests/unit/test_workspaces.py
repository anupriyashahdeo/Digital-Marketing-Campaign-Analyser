from fastapi.testclient import TestClient
from sqlalchemy import select

from ada.db.models import Membership, User
from ada.main import app
from tests.unit.test_auth import signup


def ws_id(c) -> int:
    return c.get("/api/v1/workspaces").json()[0]["id"]


def new_run(c, wid, **body):
    return c.post(f"/api/v1/workspaces/{wid}/runs", json={"category": "running shoes", **body})


def test_signup_creates_owned_workspace_and_empty_dashboard(client):
    c, _ = client
    signup(c)
    wss = c.get("/api/v1/workspaces").json()
    assert len(wss) == 1 and wss[0]["role"] == "owner"
    d = c.get(f"/api/v1/workspaces/{wss[0]['id']}/dashboard").json()
    assert d["stats"]["total_runs"] == 0 and d["recent_runs"] == [] and d["can_edit"] is True


def test_create_run_shows_on_dashboard(client):
    c, _ = client
    signup(c)
    wid = ws_id(c)
    r = new_run(c, wid, keywords=["Nike", "nike", "  Adidas  ", ""])
    assert r.status_code == 201
    run = r.json()
    assert run["status"] == "queued" and run["keywords"] == ["Nike", "Adidas"]
    assert run["created_at"].endswith("Z")
    d = c.get(f"/api/v1/workspaces/{wid}/dashboard").json()
    assert d["stats"]["total_runs"] == 1 and d["stats"]["active_runs"] == 1
    assert d["recent_runs"][0]["id"] == run["id"]
    assert c.get(f"/api/v1/workspaces/{wid}/runs").json()["total"] == 1


def test_routes_require_sign_in(client):
    c, _ = client
    assert c.get("/api/v1/workspaces").status_code == 401
    assert c.get("/api/v1/workspaces/1/dashboard").status_code == 401
    assert new_run(c, 1).status_code == 401


def test_other_workspaces_are_invisible(client):
    a, _ = client
    signup(a, "a@example.com")
    wid = ws_id(a)
    run_id = new_run(a, wid).json()["id"]

    b = TestClient(app)                  # separate cookie jar = separate user
    signup(b, "b@example.com")
    for path in (f"/workspaces/{wid}/dashboard", f"/workspaces/{wid}/runs",
                 f"/workspaces/{wid}/runs/{run_id}"):
        assert b.get(f"/api/v1{path}").status_code == 404
    assert new_run(b, wid).status_code == 404
    assert b.post(f"/api/v1/workspaces/{wid}/runs/{run_id}/cancel").status_code == 404
    # A's run id under B's own workspace must not leak either
    assert b.get(f"/api/v1/workspaces/{ws_id(b)}/runs/{run_id}").status_code == 404


def test_viewer_cannot_create_or_cancel(client):
    c, Session = client
    signup(c)
    wid = ws_id(c)
    run_id = new_run(c, wid).json()["id"]
    with Session() as s:
        uid = s.scalar(select(User.id))
        s.scalar(select(Membership).where(Membership.user_id == uid)).role = "viewer"
        s.commit()
    assert new_run(c, wid).status_code == 403
    assert c.post(f"/api/v1/workspaces/{wid}/runs/{run_id}/cancel").status_code == 403
    d = c.get(f"/api/v1/workspaces/{wid}/dashboard").json()
    assert d["can_edit"] is False and d["stats"]["total_runs"] == 1


def test_active_run_cap_and_cancel(client):
    c, _ = client
    signup(c)
    wid = ws_id(c)
    ids = [new_run(c, wid).json()["id"] for _ in range(3)]
    assert new_run(c, wid).status_code == 429
    assert c.post(f"/api/v1/workspaces/{wid}/runs/{ids[0]}/cancel").json()["status"] == "cancelled"
    assert c.post(f"/api/v1/workspaces/{wid}/runs/{ids[0]}/cancel").status_code == 409
    assert new_run(c, wid).status_code == 201


def test_run_input_validation(client):
    c, _ = client
    signup(c)
    wid = ws_id(c)
    assert new_run(c, wid, category=" a ").status_code == 422
    assert new_run(c, wid, category="x" * 121).status_code == 422
    assert new_run(c, wid, region="US").status_code == 422
    assert new_run(c, wid, language="xx").status_code == 422
    assert new_run(c, wid, keywords=["k"] * 11).status_code == 422
    assert new_run(c, wid, keywords=["x" * 61]).status_code == 422
    assert c.get(f"/api/v1/workspaces/{wid}/runs?status=bogus").status_code == 422
    assert c.get(f"/api/v1/workspaces/{wid}/runs?limit=1000").status_code == 422


def test_security_headers(client):
    c, _ = client
    h = c.get("/health").headers
    assert h["X-Content-Type-Options"] == "nosniff" and h["X-Frame-Options"] == "DENY"
