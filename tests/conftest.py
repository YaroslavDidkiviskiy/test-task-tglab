import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum!")
os.environ.setdefault("DEBUG", "true")

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db import Base, get_db

engine_test = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
AsyncSessionTest = async_sessionmaker(engine_test, expire_on_commit=False)


async def override_get_db():
    async with AsyncSessionTest() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def prepare_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def chief_token(client: AsyncClient) -> str:
    await client.post("/auth/register", json={
        "email": "chief@test.com", "name": "Chief", "password": "Password1", "role": "chief"
    })
    resp = await client.post("/auth/login", data={"username": "chief@test.com", "password": "Password1"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def member_token(client: AsyncClient) -> str:
    await client.post("/auth/register", json={
        "email": "member@test.com", "name": "Member", "password": "Password1", "role": "member"
    })
    resp = await client.post("/auth/login", data={"username": "member@test.com", "password": "Password1"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def member2_token(client: AsyncClient) -> str:
    await client.post("/auth/register", json={
        "email": "member2@test.com", "name": "Member2", "password": "Password1", "role": "member"
    })
    resp = await client.post("/auth/login", data={"username": "member2@test.com", "password": "Password1"})
    return resp.json()["access_token"]