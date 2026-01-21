from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import shutil
import json
from contextlib import asynccontextmanager
from app.database import Base, engine as prod_engine, SessionLocal, get_db, SourceFile, SourceData, PSDFile, LayerMapping
from app.excel_service import ExcelService
from app.tkq import broker, generate_psd_task, verify_psd_task

def get_engine():
    return prod_engine

def create_tables(engine_to_use=None):
    if engine_to_use is None:
        engine_to_use = get_engine()
    Base.metadata.create_all(bind=engine_to_use)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables only if not explicitly disabled (e.g. for testing)
    if os.getenv("SKIP_DB_INIT") != "1":
        create_tables()
    
    if not broker.is_worker_process:
        await broker.startup()
    yield
    if not broker.is_worker_process:
        await broker.shutdown()

app = FastAPI(title="LetakMaster API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload/excel")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 1. Register file in DB
        db_file = SourceFile(filename=file.filename, path=file_path)
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        # 2. Parse file
        service = ExcelService()
        parsed_data = service.parse_file(file_path, header_row=6)
        
        # 3. Store data in DB
        for row_idx, row in enumerate(parsed_data):
            for col_name, cell_data in row.items():
                db_data = SourceData(
                    source_file_id=db_file.id,
                    row_index=row_idx + 7, # 7 because header is at 6
                    column_name=col_name,
                    value=str(cell_data["value"]) if cell_data["value"] is not None else None,
                    formatting_json=json.dumps(cell_data["formatting"])
                )
                db.add(db_data)
        
        db.commit()
        
        return {"file_id": db_file.id, "rows_imported": len(parsed_data)}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/psd/register")
async def register_psd(filename: str, path: str, db: Session = Depends(get_db)):
    db_psd = PSDFile(filename=filename, path=path)
    db.add(db_psd)
    db.commit()
    db.refresh(db_psd)
    return db_psd

@app.post("/psd/{psd_id}/generate")
async def trigger_psd_generation(psd_id: int):
    task = await generate_psd_task.kiq(psd_id)
    return {"task_id": task.task_id}

@app.post("/psd/{psd_id}/verify")
async def trigger_psd_verification(psd_id: int):
    task = await verify_psd_task.kiq(psd_id)
    return {"task_id": task.task_id}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    # InMemoryBroker doesn't support persistent result storage by default 
    # in the same way Redis does, but for MVP it works in-memory.
    # Note: In a real multi-process env, this would need a ResultBackend.
    return {"status": "In-memory tasks are executed immediately by InMemoryBroker"}

@app.get("/source-files")
async def list_source_files(db: Session = Depends(get_db)):
    return db.query(SourceFile).all()

@app.get("/psd-files")
async def list_psd_files(db: Session = Depends(get_db)):
    return db.query(PSDFile).all()

@app.get("/source-files/{file_id}/data")
async def get_source_file_data(file_id: int, db: Session = Depends(get_db)):
    return db.query(SourceData).filter(SourceData.source_file_id == file_id).all()
