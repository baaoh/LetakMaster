import subprocess
import json
import os

def open_file_dialog(title="Select Master Excel File", file_types="Excel Files|*.xls;*.xlsx|All Files|*.*"):
    """
    Opens a modern Windows file dialog using PowerShell (WPF).
    Returns the selected path or None.
    """
    # WPF Filter format is "Label|*.ext|Label2|*.ext2"
    ps_script = f"""
    Add-Type -AssemblyName PresentationFramework
    $f = New-Object Microsoft.Win32.OpenFileDialog
    $f.Title = "{title}"
    $f.Filter = "{file_types}"
    $res = $f.ShowDialog()
    if ($res) {{
        return $f.FileName
    }}
    """
    
    try:
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        result = subprocess.run(command, capture_output=True, text=True)
        path = result.stdout.strip()
        return path if path else None
    except Exception as e:
        print(f"Error opening dialog: {e}")
        return None

def save_file_dialog(default_name="Workspace.xlsx", title="Save Workspace Copy As", file_types="Excel Files|*.xlsx|All Files|*.*"):
    """
    Opens a modern Windows Save As dialog using PowerShell (WPF).
    Returns the selected path or None.
    """
    ps_script = f"""
    Add-Type -AssemblyName PresentationFramework
    $f = New-Object Microsoft.Win32.SaveFileDialog
    $f.Title = "{title}"
    $f.Filter = "{file_types}"
    $f.FileName = "{default_name}"
    $res = $f.ShowDialog()
    if ($res) {{
        return $f.FileName
    }}
    """
    
    try:
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        result = subprocess.run(command, capture_output=True, text=True)
        path = result.stdout.strip()
        return path if path else None
    except Exception as e:
        print(f"Error opening save dialog: {e}")
        return None

def protect_file(file_path):
    """
    Sets the file attributes to Read-Only and Hidden on Windows.
    This prevents accidental modification or deletion by users.
    """
    if not os.path.exists(file_path):
        return
    
    try:
        # Use attrib command for Windows (universally available)
        # +R = Read Only, +H = Hidden
        subprocess.run(["attrib", "+R", "+H", file_path], check=True)
    except Exception as e:
        print(f"Failed to protect file {file_path}: {e}")
