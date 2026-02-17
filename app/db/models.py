from pydantic import BaseModel, Field
from datetime import datetime


class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationDocument(BaseModel):
    """Shape of documents in the `conversations` collection."""
    user_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    messages: list[ConversationMessage] = []


class GapFillExerciseItem(BaseModel):
    phrasal_verb: str
    sentence: str
    blank_sentence: str


class GapFillExerciseDocument(BaseModel):
    """Shape of documents in the `gap_fill_exercises` collection."""
    user_id: str
    conversation_id: str
    phrasal_verbs: list[str]
    exercises: list[GapFillExerciseItem]
    created_at: datetime = Field(default_factory=datetime.utcnow)
