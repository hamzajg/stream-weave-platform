"""Hand walk of VALIDATION.md's demo script against a live uvicorn on :8123."""

import json
import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8123"
PW = "correct-horse-123"


def show(step, response):
    body = response.text
    if len(body) > 220:
        body = body[:220] + "…"
    print(f"{step}: {response.status_code} {body}")
    return response


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=10)

    owner_email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    show("register owner", c.post("/api/auth/register", json={
        "email": owner_email, "password": PW, "full_name": "Owner"}))
    token = c.post("/api/auth/login", json={"email": owner_email, "password": PW}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    org = show("create org", c.post("/api/orgs", headers=h, json={
        "name": "Acme Corp", "industry": "manufacturing", "size": "11-50"})).json()

    wf = show("create workflow", c.post("/api/workflows", headers=h, json={
        "organization_id": org["id"], "name": "Invoice Triage",
        "description": "Route invoices"})).json()

    graph = {
        "nodes": [
            {"id": "t1", "type": "trigger", "label": "New invoice"},
            {"id": "a1", "type": "agent", "label": "Classify"},
            {"id": "x1", "type": "action", "label": "File it"},
        ],
        "edges": [{"source": "t1", "target": "a1"}, {"source": "a1", "target": "x1"}],
    }
    show("save draft", c.put(f"/api/workflows/{wf['id']}/draft", headers=h, json=graph))

    bad = {"nodes": graph["nodes"], "edges": [{"source": "t1", "target": "ghost"}]}
    show("reject bad edge", c.put(f"/api/workflows/{wf['id']}/draft", headers=h, json=bad))

    show("publish", c.post(f"/api/workflows/{wf['id']}/publish", headers=h))
    show("after publish", c.get(f"/api/workflows/{wf['id']}", headers=h))
    show("versions", c.get(f"/api/workflows/{wf['id']}/versions", headers=h))

    graph2 = {"nodes": graph["nodes"], "edges": graph["edges"][:1]}
    show("edit draft after publish",
         c.put(f"/api/workflows/{wf['id']}/draft", headers=h, json=graph2))
    versions = c.get(f"/api/workflows/{wf['id']}/versions", headers=h).json()
    v1, v2 = versions[-1], versions[0]
    print("published v1:", len(v1["definition"]["nodes"]), "nodes",
          len(v1["definition"]["edges"]), "edges |",
          "draft v2:", len(v2["definition"]["nodes"]), "nodes",
          len(v2["definition"]["edges"]), "edges")

    # viewer
    viewer_email = f"viewer-{uuid.uuid4().hex[:8]}@example.com"
    c.post("/api/auth/register", json={"email": viewer_email, "password": PW, "full_name": "Viewer User"})
    vtoken = c.post("/api/auth/login", json={"email": viewer_email, "password": PW}).json()["access_token"]
    vh = {"Authorization": f"Bearer {vtoken}"}
    invite = c.post(f"/api/orgs/{org['id']}/invite", headers=h,
                    json={"email": viewer_email, "role": "viewer"})
    print("invite viewer:", invite.status_code)
    token = invite.json().get("token")
    if token:
        show("accept invite", c.post("/api/orgs/invitations/accept", headers=vh,
                                     json={"token": token}))
    else:
        print("invite response has no token field — viewer check skipped")

    show("viewer read", c.get(f"/api/workflows/{wf['id']}", headers=vh))
    show("viewer publish attempt", c.post(f"/api/workflows/{wf['id']}/publish", headers=vh))

    # outsider
    out_email = f"outsider-{uuid.uuid4().hex[:8]}@example.com"
    c.post("/api/auth/register", json={"email": out_email, "password": PW, "full_name": "Outsider User"})
    otoken = c.post("/api/auth/login", json={"email": out_email, "password": PW}).json()["access_token"]
    oh = {"Authorization": f"Bearer {otoken}"}
    c.post("/api/orgs", headers=oh, json={"name": "Globex", "industry": "finance", "size": "1-10"})
    show("outsider fetch", c.get(f"/api/workflows/{wf['id']}", headers=oh))
    show("outsider list", c.get("/api/workflows", headers=oh))
    return 0


if __name__ == "__main__":
    sys.exit(main())
