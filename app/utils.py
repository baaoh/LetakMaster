import subprocess
import json

def open_file_dialog(title="Select Master Excel File", file_types="Excel Files (*.xls;*.xlsx)|*.xls;*.xlsx"):
    """
    Opens a native Windows file dialog using PowerShell.
    Returns the selected path or None.
    """
    ps_script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    $f = New-Object System.Windows.Forms.OpenFileDialog
    $f.Title = "{title}"
    $f.Filter = "{file_types}"
    $f.ShowHelp = $true
    if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
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
