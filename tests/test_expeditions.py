import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def future_expedition() -> dict:
    return {
        "title": "Test Expedition",
        "description": "desc",
        "start_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "capacity": 10,
    }


# --- CREATE ---

async def test_create_expedition_as_chief(client: AsyncClient, chief_token: str):
    resp = await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))
    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"


async def test_create_expedition_as_member_forbidden(client: AsyncClient, member_token: str):
    resp = await client.post("/expeditions", json=future_expedition(), headers=auth(member_token))
    assert resp.status_code == 403


async def test_create_expedition_unauthorized(client: AsyncClient):
    resp = await client.post("/expeditions", json=future_expedition())
    assert resp.status_code == 401


# --- STATUS TRANSITIONS ---

async def test_set_ready(client: AsyncClient, chief_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()
    resp = await client.post(f"/expeditions/{exp['id']}/status/ready", headers=auth(chief_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


async def test_set_ready_as_member_forbidden(client: AsyncClient, chief_token: str, member_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()
    resp = await client.post(f"/expeditions/{exp['id']}/status/ready", headers=auth(member_token))
    assert resp.status_code == 403


async def test_invalid_transition(client: AsyncClient, chief_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()
    resp = await client.post(f"/expeditions/{exp['id']}/status/active", headers=auth(chief_token))
    assert resp.status_code == 400


async def test_set_active_success(client: AsyncClient, chief_token: str, member_token: str, member2_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()
    exp_id = exp["id"]

    me1 = (await client.get("/expeditions", headers=auth(member_token))).json()
    reg1 = (await client.post("/auth/register", json={
        "email": "m1@test.com", "name": "M1", "password": "Password1", "role": "member"
    }))
    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    member_id = get_user_id(member_token)
    member2_id = get_user_id(member2_token)

    await client.post(f"/expeditions/{exp_id}/members", json={"user_id": member_id}, headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/members", json={"user_id": member2_id}, headers=auth(chief_token))

    # підтверджуємо
    await client.post(f"/expeditions/{exp_id}/members/confirm", headers=auth(member_token))
    await client.post(f"/expeditions/{exp_id}/members/confirm", headers=auth(member2_token))

    await client.post(f"/expeditions/{exp_id}/status/ready", headers=auth(chief_token))
    resp = await client.post(f"/expeditions/{exp_id}/status/active", headers=auth(chief_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_set_active_not_enough_members(client: AsyncClient, chief_token: str, member_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()
    exp_id = exp["id"]

    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    member_id = get_user_id(member_token)
    await client.post(f"/expeditions/{exp_id}/members", json={"user_id": member_id}, headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/members/confirm", headers=auth(member_token))
    await client.post(f"/expeditions/{exp_id}/status/ready", headers=auth(chief_token))

    resp = await client.post(f"/expeditions/{exp_id}/status/active", headers=auth(chief_token))
    assert resp.status_code == 400


# --- INVITE ---

async def test_invite_member_success(client: AsyncClient, chief_token: str, member_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()

    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    member_id = get_user_id(member_token)
    resp = await client.post(f"/expeditions/{exp['id']}/members", json={"user_id": member_id}, headers=auth(chief_token))
    assert resp.status_code == 201
    assert resp.json()["state"] == "invited"


async def test_invite_duplicate(client: AsyncClient, chief_token: str, member_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()

    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    member_id = get_user_id(member_token)
    await client.post(f"/expeditions/{exp['id']}/members", json={"user_id": member_id}, headers=auth(chief_token))
    resp = await client.post(f"/expeditions/{exp['id']}/members", json={"user_id": member_id}, headers=auth(chief_token))
    assert resp.status_code == 409


async def test_invite_chief_as_member_forbidden(client: AsyncClient, chief_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()

    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    chief_id = get_user_id(chief_token)
    resp = await client.post(f"/expeditions/{exp['id']}/members", json={"user_id": chief_id}, headers=auth(chief_token))
    assert resp.status_code == 400


# --- CONFIRM ---

async def test_confirm_success(client: AsyncClient, chief_token: str, member_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()

    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    member_id = get_user_id(member_token)
    await client.post(f"/expeditions/{exp['id']}/members", json={"user_id": member_id}, headers=auth(chief_token))
    resp = await client.post(f"/expeditions/{exp['id']}/members/confirm", headers=auth(member_token))
    assert resp.status_code == 200
    assert resp.json()["state"] == "confirmed"


async def test_confirm_twice(client: AsyncClient, chief_token: str, member_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()

    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    member_id = get_user_id(member_token)
    await client.post(f"/expeditions/{exp['id']}/members", json={"user_id": member_id}, headers=auth(chief_token))
    await client.post(f"/expeditions/{exp['id']}/members/confirm", headers=auth(member_token))
    resp = await client.post(f"/expeditions/{exp['id']}/members/confirm", headers=auth(member_token))
    assert resp.status_code == 400


# --- FINISHED ---

async def test_set_finished(client: AsyncClient, chief_token: str, member_token: str, member2_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()
    exp_id = exp["id"]

    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    member_id = get_user_id(member_token)
    member2_id = get_user_id(member2_token)

    await client.post(f"/expeditions/{exp_id}/members", json={"user_id": member_id}, headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/members", json={"user_id": member2_id}, headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/members/confirm", headers=auth(member_token))
    await client.post(f"/expeditions/{exp_id}/members/confirm", headers=auth(member2_token))
    await client.post(f"/expeditions/{exp_id}/status/ready", headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/status/active", headers=auth(chief_token))

    resp = await client.post(f"/expeditions/{exp_id}/status/finished", headers=auth(chief_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "finished"


async def test_cannot_reactivate_finished(client: AsyncClient, chief_token: str, member_token: str, member2_token: str):
    exp = (await client.post("/expeditions", json=future_expedition(), headers=auth(chief_token))).json()
    exp_id = exp["id"]

    import base64, json as j
    def get_user_id(token: str) -> str:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        return j.loads(base64.b64decode(payload))["sub"]

    member_id = get_user_id(member_token)
    member2_id = get_user_id(member2_token)

    await client.post(f"/expeditions/{exp_id}/members", json={"user_id": member_id}, headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/members", json={"user_id": member2_id}, headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/members/confirm", headers=auth(member_token))
    await client.post(f"/expeditions/{exp_id}/members/confirm", headers=auth(member2_token))
    await client.post(f"/expeditions/{exp_id}/status/ready", headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/status/active", headers=auth(chief_token))
    await client.post(f"/expeditions/{exp_id}/status/finished", headers=auth(chief_token))

    resp = await client.post(f"/expeditions/{exp_id}/status/ready", headers=auth(chief_token))
    assert resp.status_code == 400
