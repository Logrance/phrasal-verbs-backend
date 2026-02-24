from fastapi import APIRouter, Depends
from starlette.requests import Request
from app.api.deps import get_current_user
from app.core.phrasal_verbs import PHRASAL_VERBS

router = APIRouter(prefix="/api/progress")


@router.post("/advance")
async def advance_progress(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["uid"]
    user_progress = request.app.state.user_progress

    progress_doc = await user_progress.find_one({"user_id": user_id})
    if progress_doc is None:
        current_index = 0
    else:
        current_index = progress_doc.get("current_index", 0)

    max_index = len(PHRASAL_VERBS) - 1
    next_index = min(current_index + 1, max_index)
    completed = next_index == max_index and current_index == max_index

    await user_progress.update_one(
        {"user_id": user_id},
        {"$set": {"current_index": next_index}},
        upsert=True,
    )

    next_verb = PHRASAL_VERBS[next_index]
    return {
        "next_phrasal_verb": next_verb["verb"],
        "level": next_verb["level"],
        "completed": completed,
    }
