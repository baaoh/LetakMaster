import os
import pathlib
import platform

class PathManager:
    """
    The 'Universal Translator' for shared network paths.
    
    Database stores: "Archives/state_1.xlsx" (Relative)
    Windows Client (L:\...) -> "L:/LetakMaster_Assets/Archives/state_1.xlsx"
    Synology Server (/vol/...) -> "/volume1/LetakMaster_Assets/Archives/state_1.xlsx"
    """
    
    def __init__(self, root_override=None):
        # Default Root from Environment Variable or System Setting
        self.root = root_override or os.getenv("LETAK_ROOT_PATH", os.getcwd())
        
        # Ensure the root uses the correct slashes for the current OS
        self.root = pathlib.Path(self.root)

    def to_full_path(self, relative_path: str) -> str:
        """
        Converts a DB relative path into a machine-specific absolute path.
        """
        if not relative_path:
            return ""
        
        # Normalize slashes (DB should store forward slashes by convention)
        clean_rel = relative_path.replace("", "/")
        
        # Join using pathlib (handles / vs \ automatically)
        full = self.root / clean_rel
        
        return str(full)

    def to_relative_path(self, absolute_path: str) -> str:
        """
        Converts a local absolute path back into a DB-friendly relative path.
        Returns the path relative to the shared root.
        """
        try:
            abs_p = pathlib.Path(absolute_path)
            # Find the path relative to our root
            rel = abs_p.relative_to(self.root)
            # Force forward slashes for the DB
            return str(rel).replace("", "/")
        except ValueError:
            # If the file is NOT in the shared root (e.g., C:/Users/Bao/Temp)
            # we return it as-is (absolute) but this usually indicates a logic error.
            return str(absolute_path).replace("", "/")

    def is_windows(self):
        return platform.system() == "Windows"
