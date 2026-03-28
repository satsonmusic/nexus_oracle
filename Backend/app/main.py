from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.agents.orchestrator import run_agent
from app.services.streaming import stream_llm

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active_connections.remove(ws)

manager = ConnectionManager()

@app.get("/")
def root():
    return {"jarvis": "online", "status": "optimal"}

@app.post("/assistant")
def assistant(payload: dict):
    # Payload expects {"input": "text", "user_id": "user_1"}
    return run_agent(payload["input"], payload.get("user_id", "default_user"))

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            msg = await ws.receive_text()
            # Stream the LLM response chunk by chunk
            for chunk in stream_llm(msg):
                await ws.send_text(chunk)
    except WebSocketDisconnect:
        manager.disconnect(ws)
        print("Client disconnected.")