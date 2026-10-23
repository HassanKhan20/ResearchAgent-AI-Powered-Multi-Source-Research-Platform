import json


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["llm"] == "heuristic"


async def test_requires_session(client):
    assert (await client.get("/api/research")).status_code == 401
    assert (await client.get("/api/research", headers={"Authorization": "Bearer nope"})).status_code == 401


async def test_research_lifecycle(client, auth):
    resp = await client.post("/api/research", json={"question": "Is the Great Wall of China visible from space?"}, headers=auth)
    assert resp.status_code == 202
    job_id = resp.json()["id"]

    # Background task has finished by the time the in-process transport returns.
    detail = (await client.get(f"/api/research/{job_id}", headers=auth)).json()
    assert detail["status"] == "completed"
    report = detail["report"]
    assert report["sources"] and report["markdown"]

    token = auth["Authorization"].split()[1]
    async with client.stream("GET", f"/api/research/{job_id}/events", params={"token": token}) as stream:
        body = ""
        async for chunk in stream.aiter_text():
            body += chunk
            if "event: done" in body:
                break
    data_lines = [json.loads(l[5:]) for l in body.splitlines() if l.startswith("data:")]
    nodes = [e["node"] for e in data_lines if e["type"] == "step" and e["status"] == "completed"]
    assert nodes[-1] == "write"

    listing = (await client.get("/api/research", headers=auth)).json()
    assert listing[0]["id"] == job_id and listing[0]["confidence"] is not None

    got = await client.get(f"/api/reports/{report['id']}", headers=auth)
    assert got.status_code == 200

    assert (await client.delete(f"/api/research/{job_id}", headers=auth)).status_code == 204
    assert (await client.get(f"/api/research/{job_id}", headers=auth)).status_code == 404


async def test_users_cannot_see_each_others_jobs(client, auth):
    job_id = (await client.post("/api/research", json={"question": "How long is the Great Wall of China?"}, headers=auth)).json()["id"]
    other = (await client.post("/api/sessions", json={})).json()["token"]
    resp = await client.get(f"/api/research/{job_id}", headers={"Authorization": f"Bearer {other}"})
    assert resp.status_code == 404
