import os
import pathlib
import platform

class PathManager:
    """
    The 'Universal Translator' for shared network paths.
    """
    
    def __init__(self, root_override=None):
        self.root = root_override or os.getenv("LETAK_ROOT_PATH", os.getcwd())
        self.root = pathlib.Path(self.root)

    def to_full_path(self, relative_path: str) -> str:
        if not relative_path:
            return ""
        
        # FIX: Correctly replace backslashes without shattering the string
        clean_rel = str(relative_path).replace("\\", "/")
        
        # Pathlib handles the join correctly for the OS
        full = self.root / clean_rel
        return str(full)

    def to_relative_path(self, absolute_path: str) -> str:
        try:
            abs_p = pathlib.Path(absolute_path)
            rel = abs_p.relative_to(self.root)
            return str(rel).replace("\\", "/")
        except ValueError:
            return str(absolute_path).replace("\\", "/")

    def is_windows(self):
        return platform.system() == "Windows"
