from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.phrasal_chat import router as phrasal_chat_router
from app.api.routes.gap_fill import router as gap_fill_router
from app.db.mongodb import lifespan

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(phrasal_chat_router)
app.include_router(gap_fill_router)
