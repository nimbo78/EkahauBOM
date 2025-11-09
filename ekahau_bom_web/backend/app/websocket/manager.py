"""WebSocket connection manager for real-time updates."""

import json
import logging
from typing import Dict, List
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts updates.

    Supports:
    - Multiple concurrent connections
    - Broadcasting to all clients
    - Sending messages to specific clients
    - Connection lifecycle management
    """

    def __init__(self):
        """Initialize connection manager."""
        # Active connections: Dict[connection_id, WebSocket]
        self.active_connections: Dict[str, WebSocket] = {}
        logger.info("[ConnectionManager] Initialized")

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            client_id: Unique identifier for this connection
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(
            f"[ConnectionManager] Client connected: {client_id} "
            f"(total: {len(self.active_connections)})"
        )

    def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            client_id: Identifier of the connection to remove
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(
                f"[ConnectionManager] Client disconnected: {client_id} "
                f"(remaining: {len(self.active_connections)})"
            )

    async def send_personal_message(self, message: dict, client_id: str) -> None:
        """
        Send a message to a specific client.

        Args:
            message: Message dict to send (will be JSON-encoded)
            client_id: Target client identifier
        """
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
                logger.debug(f"[ConnectionManager] Sent message to {client_id}: {message['type']}")
            except Exception as e:
                logger.error(f"[ConnectionManager] Error sending to {client_id}: {e}")
                # Remove dead connection
                self.disconnect(client_id)

    async def broadcast(self, message: dict, exclude_client: str | None = None) -> None:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dict to broadcast (will be JSON-encoded)
            exclude_client: Optional client_id to exclude from broadcast
        """
        logger.info(
            f"[ConnectionManager] Broadcasting '{message['type']}' "
            f"to {len(self.active_connections)} clients"
        )

        dead_connections: List[str] = []

        for client_id, websocket in self.active_connections.items():
            if exclude_client and client_id == exclude_client:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"[ConnectionManager] Error broadcasting to {client_id}: {e}")
                dead_connections.append(client_id)

        # Clean up dead connections
        for client_id in dead_connections:
            self.disconnect(client_id)

    async def send_batch_update(
        self,
        batch_id: UUID,
        status: str,
        progress: int | None = None,
        message: str | None = None,
    ) -> None:
        """
        Broadcast batch status update to all clients.

        Args:
            batch_id: Batch UUID
            status: New batch status
            progress: Optional progress percentage (0-100)
            message: Optional status message
        """
        update_message = {
            "type": "batch_update",
            "data": {
                "batch_id": str(batch_id),
                "status": status,
                "progress": progress,
                "message": message,
            },
        }
        await self.broadcast(update_message)

    async def send_project_update(
        self,
        batch_id: UUID,
        project_id: UUID,
        status: str,
        message: str | None = None,
    ) -> None:
        """
        Broadcast project status update to all clients.

        Args:
            batch_id: Parent batch UUID
            project_id: Project UUID
            status: New project status
            message: Optional status message
        """
        update_message = {
            "type": "project_update",
            "data": {
                "batch_id": str(batch_id),
                "project_id": str(project_id),
                "status": status,
                "message": message,
            },
        }
        await self.broadcast(update_message)

    async def send_batch_created(self, batch_id: UUID) -> None:
        """
        Notify clients that a new batch was created.

        Args:
            batch_id: Newly created batch UUID
        """
        update_message = {
            "type": "batch_created",
            "data": {"batch_id": str(batch_id)},
        }
        await self.broadcast(update_message)

    async def send_batch_deleted(self, batch_id: UUID) -> None:
        """
        Notify clients that a batch was deleted.

        Args:
            batch_id: Deleted batch UUID
        """
        update_message = {
            "type": "batch_deleted",
            "data": {"batch_id": str(batch_id)},
        }
        await self.broadcast(update_message)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


# Singleton instance
connection_manager = ConnectionManager()
