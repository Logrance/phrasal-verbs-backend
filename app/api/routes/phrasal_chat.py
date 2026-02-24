from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
from app.core.config import settings
from app.api.deps import verify_firebase_token
from app.core.phrasal_verbs import PHRASAL_VERBS
from openai import AsyncOpenAI
import json

router = APIRouter()

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT_TEMPLATE = (
    "You are an English language tutor specializing in phrasal verbs. "
    "Focus this conversation entirely on the phrasal verb '{verb}' (CEFR {level}). "
    "Introduce it naturally, use it in context, explain its meaning and usage, "
    "and encourage the student to use it themselves."
)


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
    user_progress = client_ws.app.state.user_progress

    # Look up (or create) user progress
    progress_doc = await user_progress.find_one({"user_id": user_id})
    if progress_doc is None:
        await user_progress.insert_one({"user_id": user_id, "current_index": 0})
        current_index = 0
    else:
        current_index = progress_doc.get("current_index", 0)

    target = PHRASAL_VERBS[current_index]
    verb = target["verb"]
    level = target["level"]

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(verb=verb, level=level)

    # Create a conversation document
    conv_doc = {
        "user_id": user_id,
        "started_at": datetime.utcnow(),
        "ended_at": None,
        "target_phrasal_verb": verb,
        "messages": [],
    }
    result = await conversations.insert_one(conv_doc)
    conversation_id = str(result.inserted_id)

    # Send session_start to the client
    await client_ws.send_text(json.dumps({
        "type": "session_start",
        "conversation_id": conversation_id,
        "current_phrasal_verb": verb,
        "level": level,
    }))

    try:
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

            # Load full conversation history to send as context
            conv = await conversations.find_one({"_id": result.inserted_id})
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in conv.get("messages", [])
            ]

            # Call OpenAI
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": system_prompt}] + history,
            )
            reply = response.choices[0].message.content

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
        print("Chat error:", e)
        await client_ws.close()
    finally:
        # Mark conversation as ended
        await conversations.update_one(
            {"_id": result.inserted_id},
            {"$set": {"ended_at": datetime.utcnow()}},
        )
