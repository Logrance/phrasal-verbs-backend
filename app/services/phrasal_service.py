from app.core.llm import generate_exercise
from app.db.mongodb import db

async def create_phrasal_exercise(phrasal_verb: str, level: str):
    exercise = generate_exercise(phrasal_verb, level)

    doc = {
        "phrasal_verb": phrasal_verb,
        "level": level,
        "exercise": exercise
    }

    await db.exercises.insert_one(doc)
    return doc
