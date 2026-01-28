Set FSO = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

' Get the absolute path of this script file
strScriptPath = Wscript.ScriptFullName
' Get the directory containing this script
strDir = FSO.GetParentFolderName(strScriptPath)

' Explicitly set the working directory to the project root
WshShell.CurrentDirectory = strDir

' Define paths
strPython = strDir & "\python_embed\pythonw.exe"
strLauncher = strDir & "\app\launcher.py"

' Check if Python environment exists
If Not FSO.FileExists(strPython) Then
    ' Fallback to python.exe if pythonw.exe is missing
    strPython = strDir & "\python_embed\python.exe"
    If Not FSO.FileExists(strPython) Then
        ' Fallback to system python
        strPython = "python"
    End If
End If

' Run the launcher script hidden (0)
' The quotes """ are essential for paths with spaces
WshShell.Run """" & strPython & """ """ & strLauncher & """", 0, False

Set WshShell = Nothing
Set FSO = Nothing
