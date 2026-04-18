# Collaboration Module for Multi-User WebSocket Rooms
# Implements real-time collaboration with UUID-based rooms

import uuid
import json
from typing import Dict, List, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)


class CollaborationRoom:
    """Represents a collaboration room with multiple participants"""
    
    def __init__(self, room_id: str, creator: str):
        self.room_id = room_id
        self.creator = creator
        self.participants: Dict[str, WebSocket] = {}
        self.created_at = datetime.now()
        self.messages: List[Dict] = []
    
    def add_participant(self, user_id: str, websocket: WebSocket):
        self.participants[user_id] = websocket
        logger.info(f"User {user_id} joined room {self.room_id}")
    
    def remove_participant(self, user_id: str):
        if user_id in self.participants:
            del self.participants[user_id]
            logger.info(f"User {user_id} left room {self.room_id}")
    
    async def broadcast(self, message: Dict, exclude: str = None):
        """Broadcast message to all participants except excluded"""
        for user_id, ws in self.participants.items():
            if user_id != exclude:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {user_id}: {e}")
    
    def get_participant_count(self) -> int:
        return len(self.participants)


class CollaborationManager:
    """Manages all collaboration rooms"""
    
    def __init__(self):
        self.rooms: Dict[str, CollaborationRoom] = {}
        self.user_rooms: Dict[str, str] = {}  # user_id -> room_id
    
    def create_room(self, creator: str) -> str:
        """Create a new collaboration room"""
        room_id = str(uuid.uuid4())[:8]  # Short UUID
        room = CollaborationRoom(room_id, creator)
        self.rooms[room_id] = room
        self.user_rooms[creator] = room_id
        logger.info(f"Room {room_id} created by {creator}")
        return room_id
    
    def join_room(self, room_id: str, user_id: str, websocket: WebSocket) -> bool:
        """Join an existing room"""
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        room.add_participant(user_id, websocket)
        self.user_rooms[user_id] = room_id
        return True
    
    def leave_room(self, user_id: str):
        """Leave current room"""
        if user_id in self.user_rooms:
            room_id = self.user_rooms[user_id]
            if room_id in self.rooms:
                self.rooms[room_id].remove_participant(user_id)
                # Remove room if empty
                if self.rooms[room_id].get_participant_count() == 0:
                    del self.rooms[room_id]
                    logger.info(f"Room {room_id} removed (empty)")
            del self.user_rooms[user_id]
    
    def get_room(self, room_id: str) -> CollaborationRoom:
        return self.rooms.get(room_id)
    
    def get_user_room(self, user_id: str) -> str:
        return self.user_rooms.get(user_id)
    
    def list_rooms(self) -> List[Dict]:
        """List all active rooms"""
        return [
            {
                "room_id": room_id,
                "participants": room.get_participant_count(),
                "creator": room.creator,
                "created_at": room.created_at.isoformat()
            }
            for room_id, room in self.rooms.items()
        ]


# Global collaboration manager
collaboration_manager = CollaborationManager()


async def handle_collab_connection(websocket: WebSocket, user_id: str):
    """Handle WebSocket connection for collaboration"""
    await websocket.accept()
    current_room = None
    
    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command")
            
            if command == "/collab create":
                room_id = collaboration_manager.create_room(user_id)
                current_room = room_id
                await websocket.send_json({
                    "type": "system",
                    "message": f"Room {room_id} created. Use /collab join {room_id} to invite others.",
                    "room_id": room_id
                })
            
            elif command == "/collab join":
                room_id = data.get("room_id")
                if collaboration_manager.join_room(room_id, user_id, websocket):
                    current_room = room_id
                    room = collaboration_manager.get_room(room_id)
                    await room.broadcast({
                        "type": "system",
                        "message": f"User {user_id} joined the room"
                    }, exclude=user_id)
                    await websocket.send_json({
                        "type": "system",
                        "message": f"Joined room {room_id}",
                        "room_id": room_id,
                        "participants": room.get_participant_count()
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Room {room_id} not found"
                    })
            
            elif command == "/collab leave":
                if current_room:
                    room = collaboration_manager.get_room(current_room)
                    if room:
                        await room.broadcast({
                            "type": "system",
                            "message": f"User {user_id} left the room"
                        }, exclude=user_id)
                    collaboration_manager.leave_room(user_id)
                    current_room = None
                    await websocket.send_json({
                        "type": "system",
                        "message": "Left the room"
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Not in a room"
                    })
            
            elif command == "/collab list":
                rooms = collaboration_manager.list_rooms()
                await websocket.send_json({
                    "type": "rooms",
                    "rooms": rooms
                })
            
            elif command == "message" and current_room:
                room = collaboration_manager.get_room(current_room)
                if room:
                    message_data = {
                        "type": "message",
                        "user": user_id,
                        "content": data.get("content", ""),
                        "timestamp": datetime.now().isoformat()
                    }
                    room.messages.append(message_data)
                    await room.broadcast(message_data, exclude=user_id)
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Unknown command"
                })
    
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected")
        if current_room:
            collaboration_manager.leave_room(user_id)
            room = collaboration_manager.get_room(current_room)
            if room:
                await room.broadcast({
                    "type": "system",
                    "message": f"User {user_id} disconnected"
                })
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if current_room:
            collaboration_manager.leave_room(user_id)