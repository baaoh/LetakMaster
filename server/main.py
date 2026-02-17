from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.api import sync
from core.models.schema import Base
from app.database import engine

# Create database tables (PostgreSQL on Synology or local SQLite)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LetakMaster Hub", version="2.0.0")

# Enable CORS so the local React frontends can talk to the Synology Hub
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the Sync API
app.include_router(sync.router)

@app.get("/")
async def root():
    return {"status": "online", "message": "LetakMaster Hub is active"}
