import subprocess
import os
import sys
import time
import webbrowser
import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def launch():
    port = 8000
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(root)
    
    log_file = os.path.join(root, "logs.txt")
    
    # If port is in use, maybe it's already running?
    if is_port_in_use(port):
        print(f"Port {port} is already in use. Opening browser...")
        webbrowser.open(f"http://127.0.0.1:{port}/launcher.html")
        return

    # Clear old logs
    try:
        with open(log_file, "w") as f:
            f.write("--- Startup Log ---
")
    except:
        pass

    # Start Backend hidden
    # Using pythonw.exe if available, otherwise python.exe
    python_exe = os.path.join(root, "python_embed", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python"

    cmd = [
        python_exe, "-m", "uvicorn", "app.main:app", 
        "--host", "127.0.0.1", "--port", str(port)
    ]
    
    # Use subprocess.CREATE_NO_WINDOW on Windows to hide the console
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    with open(log_file, "a") as f:
        proc = subprocess.Popen(
            cmd, 
            stdout=f, 
            stderr=f, 
            creationflags=creation_flags,
            cwd=root
        )

    # Wait for startup
    max_tries = 30
    for i in range(max_tries):
        if is_port_in_use(port):
            break
        time.sleep(0.5)
    
    # Open Launcher Page
    webbrowser.open(f"http://127.0.0.1:{port}/launcher.html")

if __name__ == "__main__":
    launch()
