from fastapi import FastAPI
from app.api.routes.phrasal_chat import router as phrasal_chat_router
from app.db.mongodb import lifespan

app = FastAPI(lifespan=lifespan)

#app.include_router(health.router)
app.include_router(phrasal_chat_router)

