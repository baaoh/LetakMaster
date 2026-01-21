from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import shutil
import json
from contextlib import asynccontextmanager
from app.database import Base, engine, get_db, SourceFile, SourceData, PSDFile, LayerMapping, AppConfig, ProjectState
from app.excel_service import ExcelService
from app.sync_service import SyncService, DiffService
from app.tkq import broker, generate_psd_task, verify_psd_task
from pydantic import BaseModel

# Initialize DB tables at startup
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
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

class ConfigRequest(BaseModel):
    master_excel_path: str
    watched_sheet_name: str | None = None
    excel_password: str | None = None

@app.get("/config")
async def get_config(db: Session = Depends(get_db)):
    path = db.query(AppConfig).filter_by(key="master_excel_path").first()
    sheet = db.query(AppConfig).filter_by(key="watched_sheet_name").first()
    password = db.query(AppConfig).filter_by(key="excel_password").first()
    return {
        "master_excel_path": path.value if path else None,
        "watched_sheet_name": sheet.value if sheet else None,
        "excel_password": password.value if password else None
    }

@app.post("/config")
async def set_config(config: ConfigRequest, db: Session = Depends(get_db)):
    # Upsert path
    path_conf = db.query(AppConfig).filter_by(key="master_excel_path").first()
    if not path_conf:
        path_conf = AppConfig(key="master_excel_path", value=config.master_excel_path)
        db.add(path_conf)
    else:
        path_conf.value = config.master_excel_path
        
    # Upsert sheet
    sheet_conf = db.query(AppConfig).filter_by(key="watched_sheet_name").first()
    if not sheet_conf:
        sheet_conf = AppConfig(key="watched_sheet_name", value=config.watched_sheet_name or "")
        db.add(sheet_conf)
    else:
        sheet_conf.value = config.watched_sheet_name or ""

        

        # Upsert password

        pass_conf = db.query(AppConfig).filter_by(key="excel_password").first()

        if not pass_conf:

            pass_conf = AppConfig(key="excel_password", value=config.excel_password or "")

            db.add(pass_conf)

        else:

            pass_conf.value = config.excel_password or ""

        

        db.commit()

        return {"status": "updated"}

    

    @app.delete("/state/{state_id}")

    async def delete_state(state_id: int, password: str, db: Session = Depends(get_db)):

        # Simple protection: Match the excel_password or a hardcoded 'admin'

        # Fetch configured password

        conf_pass = db.query(AppConfig).filter_by(key="excel_password").first()

        stored_pass = conf_pass.value if conf_pass else ""

        

        if password != stored_pass and password != "admin":

            raise HTTPException(status_code=403, detail="Invalid password")

    

        state = db.query(ProjectState).get(state_id)

        if not state:

            raise HTTPException(status_code=404, detail="State not found")

            

        db.delete(state)

        db.commit()

        return {"status": "deleted"}

    

    @app.post("/sync")

    
async def trigger_sync(db: Session = Depends(get_db)):
    # For MVP, user_id is hardcoded or comes from auth later
    syncer = SyncService(db)
    try:
        result = syncer.sync_now("current_user")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(db: Session = Depends(get_db)):
    states = db.query(ProjectState).order_by(ProjectState.created_at.desc()).all()
    # Don't send large blob in list
    return [{"id": s.id, "created_at": s.created_at, "created_by": s.created_by, "excel_hash": s.excel_hash} for s in states]

@app.get("/state/{state_id}/data")
async def get_state_data(state_id: int, db: Session = Depends(get_db)):
    state = db.query(ProjectState).get(state_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    return json.loads(state.data_snapshot_json)

@app.get("/diff/{id1}/{id2}")
async def get_diff(id1: int, id2: int, db: Session = Depends(get_db)):
    s1 = db.query(ProjectState).get(id1)
    s2 = db.query(ProjectState).get(id2)
    if not s1 or not s2:
        raise HTTPException(status_code=404, detail="State not found")
    
    differ = DiffService()
    # Flattening logic might be needed here depending on how we stored it?
    # SyncService stores the raw output of ExcelService (list of dicts).
    data1 = json.loads(s1.data_snapshot_json)
    data2 = json.loads(s2.data_snapshot_json)
    
    # We assume 'column_name' isn't key, but we need a key.
    # ExcelService returns: [{"ColA": {val:..., fmt:...}, "ColB": ...}, ...]
    # This structure is hard to diff directly with generic diff logic requiring a PK.
    # For MVP Diff, we can try to "flatten" it to just values for comparison:
    # [{"ColA": "valA", "ColB": "valB"}, ...]
    
    def flatten(rows):
        flat = []
        for r in rows:
            item = {}
            for k, v in r.items():
                item[k] = v.get("value")
            flat.append(item)
        return flat

    return differ.compare(flatten(data1), flatten(data2)) # No key_field, so naive comparison

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
