"""WebSocket API endpoint for real-time updates."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time batch/project updates.

    Clients connect to this endpoint to receive real-time notifications about:
    - Batch status changes
    - Project processing updates
    - New batches created
    - Batches deleted

    Message format:
    {
        "type": "batch_update" | "project_update" | "batch_created" | "batch_deleted" | "ping" | "pong",
        "data": {
            // Type-specific payload
        }
    }

    Connection lifecycle:
    1. Client connects → receives connection confirmation
    2. Client sends ping every 30s → server responds with pong
    3. Server broadcasts updates to all clients
    4. Client disconnects → connection cleaned up
    """
    # Generate unique client ID
    client_id = str(uuid.uuid4())

    # Accept connection
    await connection_manager.connect(websocket, client_id)

    # Send connection confirmation
    await connection_manager.send_personal_message(
        {"type": "connection_established", "data": {"client_id": client_id}},
        client_id,
    )

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()

            # Handle ping/pong for keep-alive
            if data.get("type") == "ping":
                await connection_manager.send_personal_message(
                    {"type": "pong", "data": {}},
                    client_id,
                )
                logger.debug(f"[WebSocket] Ping/Pong with client {client_id}")

            # Clients can request connection count
            elif data.get("type") == "get_connection_count":
                count = connection_manager.get_connection_count()
                await connection_manager.send_personal_message(
                    {"type": "connection_count", "data": {"count": count}},
                    client_id,
                )

            # Ignore other client messages (we only broadcast server-side events)
            else:
                logger.warning(
                    f"[WebSocket] Unknown message type from {client_id}: {data.get('type')}"
                )

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Client {client_id} disconnected normally")
        connection_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"[WebSocket] Error with client {client_id}: {e}")
        connection_manager.disconnect(client_id)
