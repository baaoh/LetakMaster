from typing import Optional
from client.automation.workspace_manager import WorkspaceManager
from client.automation.layout_engine import LayoutEngine
from client.automation.json_generator import JsonGenerator
from client.automation.ps_bridge import PSBridge

class DesignerService:
    """
    Lightweight Orchestrator for Designer Hands.
    Delegates specialized tasks to modular sub-scripts.
    """
    def __init__(self):
        self.workspace = WorkspaceManager()
        self.engine = LayoutEngine()
        self.generator = JsonGenerator()
        self.ps = PSBridge()

    def open_excel(self, file_path: str, sheet_name: Optional[str] = None, password: Optional[str] = None):
        return self.workspace.open_and_extract(file_path, sheet_name, password)

    def launch_photoshop(self):
        return self.ps.launch_ps()

    def enrich_active_sheet(self):
        return self.engine.run_enrichment()

    def export_build_plans(self):
        return self.generator.run_export()

    def run_photoshop_builder(self, images_dir: Optional[str] = None):
        return self.ps.trigger_builder(images_dir)
