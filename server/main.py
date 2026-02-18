from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from server.api import sync
from core.models.schema import Base
from core.database import engine
import time
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hub")

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LetakMaster Hub", version="2.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging Middleware to see exactly what's failing on the Hub
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms")
    return response

# Include the Sync API
app.include_router(sync.router)

@app.get("/")
async def root():
    return {"status": "online", "message": "LetakMaster Hub is active"}
