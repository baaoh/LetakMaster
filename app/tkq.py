import taskiq_fastapi
from taskiq import InMemoryBroker
from app.database import SessionLocal
from app.bridge_service import BridgeService

broker = InMemoryBroker()

@broker.task
async def generate_psd_task(psd_id: int, output_path: str = None):
    db = SessionLocal()
    try:
        service = BridgeService(db)
        result_path = service.update_psd_from_db(psd_id, output_path)
        return {"status": "success", "path": result_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@broker.task
async def verify_psd_task(psd_id: int):
    db = SessionLocal()
    try:
        service = BridgeService(db)
        report = service.verify_psd(psd_id)
        return report
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
