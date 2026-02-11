from pymongo import AsyncMongoClient
from app.core.config import settings
from fastapi import FastAPI
from contextlib import asynccontextmanager
from pymongo.server_api import ServerApi

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient(
        settings.MONGO_URI,
        server_api=ServerApi("1")
    )

    app.state.mongo_client = client
    app.state.db = client[settings.Mongo_DB]
    app.state.collection = app.state.db["phrasal_data"]
    print("MongoDB connected")

    try:
        yield
    finally:
        await client.close()
        print("MongoDB disconnected")
