from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import websockets
from datetime import datetime
from app.core.config import settings

router = APIRouter()

COLAB_WS = settings.COLAB_WS_URL



@router.websocket("/ws/chat")
async def chat_proxy(client_ws: WebSocket):
    await client_ws.accept()

    try:
        async with websockets.connect(COLAB_WS) as colab_ws:
            while True:
                # 1. receive message from browser
                user_msg = await client_ws.receive_text()

                # 2. forward to colab
                await colab_ws.send(user_msg)

                # 3. wait for model reply
                reply = await colab_ws.recv()

                #mongodb
                collection = client_ws.app.state.collection
                await collection.insert_one({
                    "message": reply,
                    "timestamp": datetime.utcnow()
                })
                

                # 4. forward back to browser
                await client_ws.send_text(reply)

    except WebSocketDisconnect:
        print("Client disconnected")

    except Exception as e:
        print("Proxy error:", e)
        await client_ws.close()

    
