Set WshShell = CreateObject("WScript.Shell")
' Get the directory of the script
strPath = WshShell.CurrentDirectory

' Construct path to pythonw.exe and the launcher script
strPython = strPath & "\python_embed\pythonw.exe"
strScript = strPath & "\app\launcher.py"

' Run the command hidden (0)
' We use quotes to handle potential spaces in paths
WshShell.Run """" & strPython & """ """ & strScript & """", 0, False

Set WshShell = Nothing
