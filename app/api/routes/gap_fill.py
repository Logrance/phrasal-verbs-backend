from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from bson import ObjectId
from starlette.requests import Request
import websockets
import json
from datetime import datetime
from app.core.config import settings

router = APIRouter(prefix="/api")

COLAB_WS = settings.COLAB_WS_URL

GAP_FILL_PROMPT_TEMPLATE = """Analyze the following conversation between a user and an English tutor.
Identify the phrasal verbs used in the conversation and generate gap-fill exercises.

Conversation:
{conversation}

Generate a JSON response with EXACTLY this structure (no other text, just the JSON):
{{
  "phrasal_verbs": ["verb1", "verb2"],
  "exercises": [
    {{
      "phrasal_verb": "verb1",
      "sentence": "Original sentence using the phrasal verb.",
      "blank_sentence": "Original sentence with _____ replacing the phrasal verb."
    }}
  ]
}}

Generate 3-5 exercises based on phrasal verbs from the conversation. If few phrasal verbs
appear in the conversation, create new example sentences using those same phrasal verbs."""


@router.post("/gap-fill/{conversation_id}")
async def generate_gap_fill(
    conversation_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["uid"]
    conversations = request.app.state.conversations
    gap_fill_exercises = request.app.state.gap_fill_exercises

    # Fetch conversation and verify ownership
    try:
        conv = await conversations.find_one({"_id": ObjectId(conversation_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your conversation")

    # Build conversation text from messages
    messages = conv.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Conversation has no messages")

    conversation_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in messages
    )

    prompt = GAP_FILL_PROMPT_TEMPLATE.format(conversation=conversation_text)

    # Send prompt to Colab LLM via WebSocket
    try:
        async with websockets.connect(COLAB_WS) as colab_ws:
            await colab_ws.send(prompt)
            reply = await colab_ws.recv()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM service error: {e}")

    # Parse the JSON response from the LLM
    try:
        # Try to extract JSON from the reply (LLM might wrap it in markdown)
        json_str = reply
        if "```json" in reply:
            json_str = reply.split("```json")[1].split("```")[0]
        elif "```" in reply:
            json_str = reply.split("```")[1].split("```")[0]
        parsed = json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        raise HTTPException(
            status_code=502,
            detail="Failed to parse LLM response as JSON",
        )

    # Store in MongoDB
    doc = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "phrasal_verbs": parsed.get("phrasal_verbs", []),
        "exercises": parsed.get("exercises", []),
        "created_at": datetime.utcnow(),
    }
    await gap_fill_exercises.insert_one(doc)

    return {
        "phrasal_verbs": doc["phrasal_verbs"],
        "exercises": doc["exercises"],
    }
