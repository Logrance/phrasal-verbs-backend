from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from bson import ObjectId
from starlette.requests import Request
from openai import AsyncOpenAI
import json
from datetime import datetime
from app.core.config import settings

router = APIRouter(prefix="/api")

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

GAP_FILL_PROMPT_TEMPLATE = """The target phrasal verb for this lesson is '{verb}'.
Generate gap-fill exercises specifically using this verb, drawn from the conversation below.

Conversation:
{conversation}

Generate a JSON response with EXACTLY this structure (no other text, just the JSON):
{{
  "phrasal_verbs": ["{verb}"],
  "exercises": [
    {{
      "phrasal_verb": "{verb}",
      "sentence": "Original sentence using the phrasal verb.",
      "blank_sentence": "Original sentence with _____ replacing the phrasal verb."
    }}
  ]
}}

Generate 3-5 exercises using '{verb}'. Draw sentences from the conversation where possible;
if the conversation contains fewer than 3 uses, create new natural example sentences using the same verb."""


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

    target_verb = conv.get("target_phrasal_verb", "phrasal verbs")

    conversation_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in messages
    )

    prompt = GAP_FILL_PROMPT_TEMPLATE.format(
        verb=target_verb,
        conversation=conversation_text,
    )

    # Send prompt to OpenAI
    try:
        response = await openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        reply = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM service error: {e}")

    # Parse the JSON response from the LLM
    try:
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
        "target_phrasal_verb": target_verb,
        "phrasal_verbs": parsed.get("phrasal_verbs", []),
        "exercises": parsed.get("exercises", []),
        "created_at": datetime.utcnow(),
    }
    await gap_fill_exercises.insert_one(doc)

    return {
        "phrasal_verbs": doc["phrasal_verbs"],
        "exercises": doc["exercises"],
    }
