import os
import win32com.client
import win32com.client.dynamic
import pythoncom
import json
import subprocess
import glob
from typing import Optional

class PSBridge:
    """
    Gold Standard Bridge to Photoshop.
    Includes COM execution and Executable Fallback from master branch.
    """
    
    def _find_photoshop_exe(self) -> Optional[str]:
        """Scans standard paths for the Photoshop executable."""
        candidates = [
            r"C:\Program Files\Adobe\Adobe Photoshop 2025\Photoshop.exe",
            r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
            r"C:\Program Files\Adobe\Adobe Photoshop 2023\Photoshop.exe",
            r"C:\Program Files\Adobe\Adobe Photoshop 2022\Photoshop.exe",
        ]
        for c in candidates:
            if os.path.exists(c): return c
        
        # Wildcard search for newer/older versions
        wildcards = glob.glob(r"C:\Program Files\Adobe\Adobe Photoshop*\Photoshop.exe")
        if wildcards:
            return sorted(wildcards)[-1] # Return newest found
        return None

    def launch_ps(self):
        """Connects to or launches Photoshop."""
        try:
            pythoncom.CoInitialize()
            # Attempt connection
            ps = win32com.client.dynamic.Dispatch("Photoshop.Application")
            ps.Visible = True
            return {"status": "success", "message": f"Linked to {ps.Name}"}
        except Exception as e:
            # Fallback: Just try to find the EXE and start it
            exe = self._find_photoshop_exe()
            if exe:
                subprocess.Popen([exe])
                return {"status": "success", "message": "Photoshop process started via EXE."}
            return {"status": "error", "message": f"Could not find or link Photoshop: {str(e)}"}
        finally:
            pythoncom.CoUninitialize()

    def trigger_builder(self, images_dir: Optional[str] = None):
        """
        Executes builder script. 
        Tries COM first, then falls back to OS command line execution.
        """
        try:
            pythoncom.CoInitialize()
            
            # 1. Path Preparation
            plans_root = os.path.join(os.getcwd(), "workspaces", "build_plans")
            subdirs = [os.path.join(plans_root, d) for d in os.listdir(plans_root) if os.path.isdir(os.path.join(plans_root, d))]
            if not subdirs: return {"status": "error", "message": "No build plans found."}
            subdirs.sort(key=os.path.getmtime, reverse=True)
            latest_plans_dir = subdirs[0]
            
            js_images_dir = json.dumps((images_dir or "").replace("\\", "/"))
            js_plans_dir = json.dumps(latest_plans_dir.replace("\\", "/"))
            
            # 2. Script Generation
            injection = (
                f"var g_injected_images_dir = {js_images_dir};\n"
                f"var g_injected_json_dir = {js_plans_dir};\n"
                f"var g_injected_automation = true;\n"
            )
            
            jsx_template = os.path.abspath("scripts/builder.jsx")
            with open(jsx_template, "r", encoding="utf-8") as f:
                content = f.read().replace("#target photoshop", "")
            
            run_script_path = os.path.abspath("scripts/run_autogen.jsx")
            with open(run_script_path, "w", encoding="utf-8") as f:
                f.write(injection + content)
            
            clean_run_path = run_script_path.replace("\\", "/")

            # 3. Execution Path A: COM (Direct)
            try:
                ps = win32com.client.dynamic.Dispatch("Photoshop.Application")
                # Attempt the call that sometimes fails with 'Required value missing'
                ps.DoJavaScriptFile(clean_run_path, [], 1)
                return {"status": "success", "message": "Builder triggered via COM."}
            except Exception as com_err:
                print(f"DEBUG: COM Trigger failed, trying EXE fallback... Error: {com_err}")
                
                # 4. Execution Path B: EXE Fallback (The 'Master' way)
                exe_path = self._find_photoshop_exe()
                if exe_path:
                    # Launching Photoshop with the script as an argument
                    subprocess.Popen([exe_path, run_script_path])
                    return {"status": "success", "message": "Builder triggered via Executable Fallback."}
                else:
                    # Path C: Last Resort (Generic OS launch)
                    os.startfile(run_script_path)
                    return {"status": "success", "message": "Builder triggered via OS startfile."}

        except Exception as e:
            return {"status": "error", "message": f"Critical Bridge Failure: {str(e)}"}
        finally:
            pythoncom.CoUninitialize()
