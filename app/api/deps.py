from fastapi import Request, HTTPException
from firebase_admin import auth


def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return the decoded payload."""
    try:
        decoded = auth.verify_id_token(token)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth_header.removeprefix("Bearer ")
    return verify_firebase_token(token)
