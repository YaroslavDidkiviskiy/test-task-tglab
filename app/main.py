from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.expeditions.router import router as expedition_router
from app.ws.router import router as ws_router

app = FastAPI(title="Expedition API", version="0.1.0")

app.include_router(auth_router)
app.include_router(expedition_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}