import json
from typing import Set
from fastapi import WebSocket

# All connected dashboard clients
_connected_clients: Set[WebSocket] = set()

async def connect_client(websocket: WebSocket):
    await websocket.accept()
    _connected_clients.add(websocket)
    print(f"[Dashboard] Client connected. Total: {len(_connected_clients)}")

def disconnect_client(websocket: WebSocket):
    _connected_clients.discard(websocket)
    print(f"[Dashboard] Client disconnected. Total: {len(_connected_clients)}")

async def broadcast_update(data: dict):
    """Send live update to all connected dashboard WebSocket clients."""
    if not _connected_clients:
        return
    message = json.dumps(data)
    dead = set()
    for client in _connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            dead.add(client)
    for d in dead:
        _connected_clients.discard(d)