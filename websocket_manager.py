from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        self.waiting_users: List[Dict] = []
        self.connected_pairs: Dict[str, str] = {}
        self.active_connections: Dict[str, WebSocket] = {}
        self.active_ips: set = set()

    async def connect(self, websocket: WebSocket, user_id: str, ip: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.active_ips.add(ip)

    async def disconnect(self, user_id: str, ip: str):
        # Remove from waiting
        self.waiting_users = [u for u in self.waiting_users if u["id"] != user_id]

        # Handle pair disconnection
        partner_id = self.connected_pairs.get(user_id)
        if partner_id:
            del self.connected_pairs[user_id]
            del self.connected_pairs[partner_id]
            # Notify partner
            online_count = self.get_online_count()
            await self.send_personal_message(json.dumps({"type": "partner-disconnected", "onlineCount": online_count}), partner_id)

        # Remove from active connections
        if user_id in self.active_connections:
            del self.active_connections[user_id]

        # Remove IP
        self.active_ips.discard(ip)

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    def get_online_count(self):
        return len(self.active_ips)

    async def pair_users(self, user_id: str):
        print(f"Pairing user {user_id}, waiting users: {len(self.waiting_users)}")
        if self.waiting_users:
            partner = self.waiting_users.pop(0)
            self.connected_pairs[user_id] = partner["id"]
            self.connected_pairs[partner["id"]] = user_id
            print(f"Paired {user_id} with {partner['id']}")
            online_count = self.get_online_count()

            # Notify both - new user creates offer, waiting user waits
            print(f"Sending matched to {user_id}")
            await self.send_personal_message(json.dumps({"type": "matched", "partnerId": partner["id"], "shouldCreateOffer": True, "onlineCount": online_count}), user_id)
            print(f"Sending matched to {partner['id']}")
            await self.send_personal_message(json.dumps({"type": "matched", "partnerId": user_id, "shouldCreateOffer": False, "onlineCount": online_count}), partner["id"])
        else:
            self.waiting_users.append({"id": user_id})
            online_count = self.get_online_count()
            print(f"Added {user_id} to waiting")
            await self.send_personal_message(json.dumps({"type": "waiting", "onlineCount": online_count}), user_id)

    async def handle_next(self, user_id: str):
        partner_id = self.connected_pairs.get(user_id)
        if partner_id:
            del self.connected_pairs[user_id]
            del self.connected_pairs[partner_id]
            # Notify partner
            online_count = self.get_online_count()
            await self.send_personal_message(json.dumps({"type": "partner-next", "onlineCount": online_count}), partner_id)
            # Add current user to waiting for new partner
            self.waiting_users.append({"id": user_id})
            # Try to pair current user with someone else
            await self.pair_users(user_id)

    async def relay_message(self, message: dict, from_user: str):
        partner_id = self.connected_pairs.get(from_user)
        print(f"Relaying {message['type']} from {from_user} to {partner_id}")
        if partner_id and partner_id in self.active_connections:
            message["from"] = from_user
            await self.active_connections[partner_id].send_text(json.dumps(message))
        else:
            print(f"No partner or not connected for {from_user}")
