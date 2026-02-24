from pymongo import AsyncMongoClient
from app.core.config import settings
from fastapi import FastAPI
from contextlib import asynccontextmanager
from pymongo.server_api import ServerApi
import firebase_admin
from firebase_admin import credentials

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate(settings.FIREBASE_SA_KEY_PATH)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin initialized")

    client = AsyncMongoClient(
        settings.MONGO_URI,
        server_api=ServerApi("1")
    )

    app.state.mongo_client = client
    app.state.db = client[settings.Mongo_DB]
    app.state.collection = app.state.db["phrasal_data"]
    app.state.conversations = app.state.db["conversations"]
    app.state.gap_fill_exercises = app.state.db["gap_fill_exercises"]
    app.state.user_progress = app.state.db["user_progress"]
    print("MongoDB connected")

    try:
        yield
    finally:
        await client.close()
        print("MongoDB disconnected")
