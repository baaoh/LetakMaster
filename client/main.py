from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.utils.config import settings
from client.api import automation

app = FastAPI(title="LetakMaster Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(automation.router)

@app.get("/")
async def root():
    return {
        "status": "online", 
        "mode": "Client Agent",
        "user": settings.user_id,
        "hub_url": settings.hub_url
    }

# This agent will eventually have routes for:
# - /automation/run-builder
# - /automation/sync-excel
# - /workspace/checkout
