from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from websocket_manager import ConnectionManager
import uuid
import json

app = FastAPI()

# CORS middleware for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

@app.get("/")
async def read_root():
    return {"message": "Suhbatdosh Video Chat Backend", "status": "running"}

@app.websocket("/ws/signaling")
async def signaling_endpoint(websocket: WebSocket):
    user_id = str(uuid.uuid4())
    print(f"WebSocket connection from {user_id}")
    await manager.connect(websocket, user_id)
    
    try:
        # Send connected message with user ID
        online_count = manager.get_online_count()
        await manager.send_personal_message(
            json.dumps({"type": "connected", "userId": user_id, "onlineCount": online_count}),
            user_id
        )
        
        # Attempt to pair the user
        await manager.pair_users(user_id)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message["type"] in ["offer", "answer", "ice-candidate"]:
                await manager.relay_message(message, user_id)
            elif message["type"] == "next":
                await manager.handle_next(user_id)
                
    except WebSocketDisconnect:
        await manager.disconnect(user_id)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False  # Set to False in production
    )
