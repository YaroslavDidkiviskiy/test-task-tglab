import uuid
import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # expedition_id -> {user_id -> WebSocket}
        self._connections: dict[uuid.UUID, dict[uuid.UUID, WebSocket]] = {}

    def connect(self, expedition_id: uuid.UUID, user_id: uuid.UUID, ws: WebSocket):
        if expedition_id not in self._connections:
            self._connections[expedition_id] = {}
        self._connections[expedition_id][user_id] = ws

    def disconnect(self, expedition_id: uuid.UUID, user_id: uuid.UUID):
        if expedition_id in self._connections:
            self._connections[expedition_id].pop(user_id, None)
            if not self._connections[expedition_id]:
                del self._connections[expedition_id]

    async def broadcast_expedition(self, expedition_id: uuid.UUID, payload: dict):
        connections = self._connections.get(expedition_id, {})
        dead = []
        for user_id, ws in connections.items():
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(user_id)
        for user_id in dead:
            self.disconnect(expedition_id, user_id)


manager = ConnectionManager()
