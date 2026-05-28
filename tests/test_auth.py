import pytest
from httpx import AsyncClient


async def test_register_success(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "test@test.com",
        "name": "Test",
        "password": "Password1",
        "role": "member",
    })
    assert resp.status_code == 201
    assert resp.json()["email"] == "test@test.com"


async def test_register_duplicate_email(client: AsyncClient):
    data = {"email": "test@test.com", "name": "Test", "password": "Password1", "role": "member"}
    await client.post("/auth/register", json=data)
    resp = await client.post("/auth/register", json=data)
    assert resp.status_code == 409


async def test_register_weak_password(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "test@test.com",
        "name": "Test",
        "password": "weakpass",
        "role": "member",
    })
    assert resp.status_code == 422


async def test_login_success(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "test@test.com",
        "name": "Test",
        "password": "Password1",
        "role": "member",
    })
    resp = await client.post("/auth/login", data={
        "username": "test@test.com",
        "password": "Password1",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "test@test.com",
        "name": "Test",
        "password": "Password1",
        "role": "member",
    })
    resp = await client.post("/auth/login", data={
        "username": "test@test.com",
        "password": "WrongPass1",
    })
    assert resp.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post("/auth/login", data={
        "username": "nobody@test.com",
        "password": "Password1",
    })
    assert resp.status_code == 401


async def test_logout(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "test@test.com",
        "name": "Test",
        "password": "Password1",
        "role": "member",
    })
    await client.post("/auth/login", data={
        "username": "test@test.com",
        "password": "Password1",
    })
    resp = await client.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
