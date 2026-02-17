import os
import sys
import psutil
import datetime
import traceback

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

LOG_FILE = "debug_system.log"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def check_excel_processes():
    log("--- Checking EXCEL.EXE processes ---")
    count = 0
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        try:
            if proc.info['name'] and 'excel.exe' in proc.info['name'].lower():
                log(f"Found Excel: PID={proc.info['pid']}, User={proc.info['username']}")
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    log(f"Total Excel Processes: {count}")
    return count

def check_com_connectivity():
    log("--- Checking COM Connectivity (xlwings) ---")
    try:
        import xlwings as xw
        # Try to connect to active app first
        if len(xw.apps) > 0:
            log(f"xlwings sees {len(xw.apps)} active apps.")
            for app in xw.apps:
                try:
                    log(f"  App PID: {app.pid}")
                    for book in app.books:
                        log(f"    Book: {book.name}")
                except Exception as e:
                    log(f"    Error inspecting app: {e}")
        else:
            log("xlwings reports 0 active apps.")
            
        # Try launching a hidden instance
        log("Attempting to launch hidden Excel instance...")
        try:
            app = xw.App(visible=False)
            log(f"Launched successfully. PID={app.pid}")
            app.quit()
            log("Quit successfully.")
        except Exception as e:
            log(f"Failed to launch/quit Excel: {e}")
            
    except Exception as e:
        log(f"CRITICAL COM ERROR: {e}")
        traceback.print_exc()

def check_file_access(path):
    log(f"--- Checking File Access: {path} ---")
    if not os.path.exists(path):
        log("File does not exist.")
        return
    
    try:
        with open(path, "r+b") as f:
            log("Successfully opened for Read/Write.")
    except Exception as e:
        log(f"Failed to open file: {e}")

if __name__ == "__main__":
    log("=== STARTING SYSTEM DEBUG ===")
    
    # Check Project State 5 (since user mentioned it)
    path = os.path.abspath(os.path.join("workspaces", "state_5", "Workspace_State_5.xlsx"))
    check_file_access(path)
    
    check_excel_processes()
    check_com_connectivity()
    
    log("=== END DEBUG ===")
