from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import websockets
from datetime import datetime
from app.core.config import settings
from app.api.deps import verify_firebase_token
import json

router = APIRouter()

COLAB_WS = settings.COLAB_WS_URL


@router.websocket("/ws/chat")
async def chat_proxy(client_ws: WebSocket, token: str = ""):
    # Verify Firebase token before accepting the connection
    try:
        decoded = verify_firebase_token(token)
        user_id = decoded["uid"]
    except Exception:
        await client_ws.close(code=4001, reason="Invalid token")
        return

    await client_ws.accept()

    conversations = client_ws.app.state.conversations

    # Create a conversation document
    conv_doc = {
        "user_id": user_id,
        "started_at": datetime.utcnow(),
        "ended_at": None,
        "messages": [],
    }
    result = await conversations.insert_one(conv_doc)
    conversation_id = str(result.inserted_id)

    # Send session_start to the client
    await client_ws.send_text(json.dumps({
        "type": "session_start",
        "conversation_id": conversation_id,
    }))

    try:
        async with websockets.connect(COLAB_WS) as colab_ws:
            while True:
                user_msg = await client_ws.receive_text()

                # Store user message
                await conversations.update_one(
                    {"_id": result.inserted_id},
                    {"$push": {"messages": {
                        "role": "user",
                        "content": user_msg,
                        "timestamp": datetime.utcnow(),
                    }}},
                )

                # Forward to Colab LLM
                await colab_ws.send(user_msg)
                reply = await colab_ws.recv()

                # Store assistant reply
                await conversations.update_one(
                    {"_id": result.inserted_id},
                    {"$push": {"messages": {
                        "role": "assistant",
                        "content": reply,
                        "timestamp": datetime.utcnow(),
                    }}},
                )

                await client_ws.send_text(reply)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print("Proxy error:", e)
        await client_ws.close()
    finally:
        # Mark conversation as ended
        await conversations.update_one(
            {"_id": result.inserted_id},
            {"$set": {"ended_at": datetime.utcnow()}},
        )
