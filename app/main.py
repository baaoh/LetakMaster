from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import shutil
import json
from app.database import Base, engine, get_db, SourceFile, SourceData
from app.excel_service import ExcelService

# Initialize DB
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LetakMaster API")

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
