from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._subscribers: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        await websocket.accept()
        self.active_connections.add(websocket)
        if channel not in self._subscribers:
            self._subscribers[channel] = set()
        self._subscribers[channel].add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        for channel_subs in self._subscribers.values():
            channel_subs.discard(websocket)

    async def broadcast(self, message: dict, channel: str = "default"):
        disconnected = set()
        target = self._subscribers.get(channel, self.active_connections)
        for connection in target:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        target -= disconnected

    async def broadcast_all(self, message: dict):
        await self.broadcast(message, "default")


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, channel: str = "default"):
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "subscribe":
                await websocket.send_json({"type": "subscribed", "channel": channel})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_update(data: dict):
    await manager.broadcast_all(data)


def get_manager() -> ConnectionManager:
    return manager