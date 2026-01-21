from sqlalchemy.orm import Session
from app.database import PSDFile, LayerMapping, SourceData
from app.psd_service import PSDService

class BridgeService:
    def __init__(self, db: Session):
        self.db = db
        self.psd_service = PSDService()

    def update_psd_from_db(self, psd_id: int, output_path: str = None):
        """
        Fetches all mappings for a PSD, gets the latest data from DB,
        and updates the actual PSD file.
        """
        psd_record = self.db.query(PSDFile).filter(PSDFile.id == psd_id).first()
        if not psd_record:
            raise ValueError(f"PSD record {psd_id} not found")

        mappings = self.db.query(LayerMapping).filter(LayerMapping.psd_file_id == psd_id).all()
        
        data_to_apply = {}
        for m in mappings:
            data_to_apply[m.layer_name] = m.source_data.value

        target_path = output_path or psd_record.path
        self.psd_service.update_layers(psd_record.path, data_to_apply, target_path)
        
        return target_path

    def verify_psd(self, psd_id: int):
        """
        Compares current PSD layer content with values in the database.
        Returns a report of discrepancies.
        """
        psd_record = self.db.query(PSDFile).filter(PSDFile.id == psd_id).first()
        if not psd_record:
            raise ValueError(f"PSD record {psd_id} not found")

        # 1. Read actual content from PSD
        actual_content = self.psd_service.read_layers(psd_record.path)
        
        # 2. Get expected content from DB mappings
        mappings = self.db.query(LayerMapping).filter(LayerMapping.psd_file_id == psd_id).all()
        
        discrepancies = []
        for m in mappings:
            expected = m.source_data.value
            actual = actual_content.get(m.layer_name)
            
            if str(actual) != str(expected):
                discrepancies.append({
                    "layer": m.layer_name,
                    "db_value": expected,
                    "psd_value": actual
                })
        
        return {
            "psd_id": psd_id,
            "status": "match" if not discrepancies else "mismatch",
            "discrepancies": discrepancies
        }
